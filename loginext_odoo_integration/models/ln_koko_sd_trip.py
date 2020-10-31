# -*- coding: utf-8 -*-.

from odoo import models, fields, api, _
from datetime import datetime, timedelta
import requests
import logging
import json
from odoo.tools import config
from odoo.addons.celery_queue.decorators import CeleryTask
from odoo.tools.profiler import profile
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class KokoSDTrip(models.Model):
    _inherit = "koko.sd.trip"

    def get_ref_by_order_name(self, orderNames):
        orderRef = []
        for name in orderNames:
            # name = 'OD-206-DELIVER'
            oid = int(name.split('-')[1])
            order_obj = self.env['koko.sd.trip.shop.details'].sudo().browse(oid)
            ref = order_obj.ln_order_ref_id if order_obj.ln_order_ref_id else order_obj.ln_pickup_order_ref_id
            orderRef.append(ref)
        return orderRef

    def update_delivery_date(self, order_ids, schedule_dt):
        '''Update todays date as a delivery date of given orders.'''
        orderList = [o.id for o in order_ids]
        self._cr.execute("UPDATE koko_sd_trip_shop_details SET delivery_date='%s' WHERE id in %s;"% (schedule_dt, tuple(orderList)))
        self._cr.commit()
        logger.info('\n========== Delivery-date-updated: ============== \n %s \n' % (len(orderList)))
        return True

    def update_P1_delivery_date(self, orders, del_dt):
        '''Update next date as a delivery date of PRIORITY1 orders.'''  
        rec = self.env['koko.sd.trip.shop.details'].sudo().search([('ln_priority','=','PRIORITY1'), ('ln_order_ref_id','in',orders)])
        self.update_delivery_date(rec, del_dt)
        return True

    def update_vehicle_ref_by_name(self, name, mediumId):
        mid = self.env['koko.dist.vehicle.config'].sudo().search([('name_for_ln','=',name.strip()), ('delivery_medium_ref_id','=',False)])
        if mid:
            mid.delivery_medium_ref_id = mediumId
            return mid.id
        return 'Delivery associated reference id not updated.'
    
    def set_priority(self, new_priority):
        api_token_obj = self.env['koko.loginext.conf'].sudo().search([], limit=1)
        api_token_obj.current_priority = new_priority if new_priority else 'PRIORITY1'
        api_token_obj._cr.commit()
        return True
    
    def set_sequence(self, oid, seq):
        # shop.sequence = int(seq)
        # shop._cr.commit()
        self._cr.execute('UPDATE koko_sd_trip_shop_details SET sequence=%s WHERE id=%s;' % (seq, oid))
        self._cr.commit()
        return True

    # @profile
    def create_trip(self, del_med_name, shopsList, delivery_date, trip_ref_id):
        '''Create trip functions.'''
        loginext_conf_obj = self.env['koko.loginext.conf'].sudo().search([], limit=1)
        vid = int(del_med_name.split('-')[1])
        vehicle_config = self.env['koko.dist.vehicle.config'].sudo().browse(vid)
        vehicle_model_id = vehicle_config.vehicle_id
        is_trip_exist = self.sudo().search([('scheduled_date','=',delivery_date), ('model_id','=',vehicle_model_id.id)])
        if not is_trip_exist:
            trip_obj = self.sudo().create({
                'model_id': vehicle_model_id.id,
                'vehicle_num': vehicle_model_id.license_plate,
                'scheduled_date': delivery_date,
                'ln_trip_ref_id': trip_ref_id,
                'created_by': 'Loginext'
            })
            loginext_conf_obj.trip_count += 1
            for shop in shopsList:
                shop.koko_sd_trip_id = trip_obj.id
                shop.state = 'planned'
            trip_obj.create_trip_stock({})
            vehicle_config.is_consumed = True
            trip_obj._cr.commit()
            vehicle_config._cr.commit()
            logger.info('======== TRIP CREATED: %s ========' % (trip_obj.id))
        else:
            logger.info('======== Vehicle already assigned: %s ========' % (vehicle_model_id.id))
        return True

    def get_final_cost(self, ttl_trip_cost_per_prod, kit_dist_config, vehicle_id, shop_orders, response):
        logger.info('\n==== KOKO COST:LOGINEXT COST ===\n')
        logger.info('%s: %s \n' % (kit_dist_config.max_logistics_cost_per_pr, ttl_trip_cost_per_prod))
        if kit_dist_config.max_logistics_cost_per_pr < ttl_trip_cost_per_prod:
            response['msg'] = """Route plan is not suitable.
                Allowed logistics cost per product: %s,
                and calculated cost per product: %s""" % (kit_dist_config.max_logistics_cost_per_pr, ttl_trip_cost_per_prod)
            return response
        response['status'] = True
        response['vehicle_id'] = vehicle_id
        response['configured_cost'] = kit_dist_config.max_logistics_cost_per_pr
        response['calculated_cost'] = ttl_trip_cost_per_prod
        response['shop_order_ids'] = shop_orders._ids
        return response

    def get_new_prods(self, shop_orders, default_fixed_time):
        ttl_fixed_minutes = 0.00
        ttl_prods = 0
        for order in shop_orders:
            ttl_fixed_minutes = ttl_fixed_minutes + order.shop_id.fixed_time > 0 and order.shop_id.fixed_time or default_fixed_time
            for st_detail in order.shop_stock_details_ids:
                ttl_prods = ttl_prods + st_detail.required_qty > 0 and st_detail.required_qty or 0
        return [ttl_prods, ttl_fixed_minutes]

    def get_trip_cost(self, params):
        """
        params: {
            'delivery_medium_name': 'DA-1',
            'orders': koko.dist.vehicle.config(1, 2),
            'trip_time': '8.50', # 8:30 hours
            'trip_km': 540,
        }
        """
        response = {'status': False}
        try:
            if 'delivery_medium_name' not in params or 'orders' not in params or 'trip_time' not in params or 'trip_km' not in params:
                response['msg'] = 'Missing some parameters. Required parameters["delivery_medium_name", "orders", "trip_time", "trip_km"]'
                return response
            vid = int(params['delivery_medium_name'].split('-')[1])
            vehicle_config = self.env['koko.dist.vehicle.config'].sudo().browse(vid)
            if not vehicle_config:
                msg = 'Vehicle Configuration not found for "Koko Distribution" with name: ' % params['delivery_medium_name']
                response['msg'] = msg
                return response
            vehicle_id = vehicle_config.vehicle_id and vehicle_config.vehicle_id.id or False
            if not vehicle_id:
                response['msg'] = 'No vehicle associated with vehicle configuration'
                return response
            total_time = self.env['res.partner'].convert_to_time(float(params['trip_time'])).split(":")
            kit_dist_config = self.env['koko.kit.dist.config'].sudo().search([], limit=1)
            if not kit_dist_config:
                response['msg'] = 'No configuration found for object "koko.kit.dist.config"'
                return response
            default_fixed_time = kit_dist_config.fixed_time
            shop_orders = params['orders']
            ttl_prods, ttl_fixed_minutes = self.get_new_prods(shop_orders, default_fixed_time)
            total_time = (int(total_time[0]) * 60) + int(total_time[1])
            vehicle_trip_minutes = (total_time - ttl_fixed_minutes)
            if ttl_prods <= 0:
                response['msg'] = "All given shop orders doesn't have any requirement to supply[Zero Qty]"
                return response
            cost_a = vehicle_config.vehicle_cost_per_km * params['trip_km']
            cost_b = vehicle_config.vehicle_cost_per_min * vehicle_trip_minutes
            cost_c = (vehicle_config.service_cost_per_min * total_time)
            cost_d = vehicle_config.fixed_cost_per_vehicle + vehicle_config.fixed_service_cost
            ttl_trip_cost_per_prod = (cost_a + cost_b + cost_c + cost_d) / ttl_prods
            return self.get_final_cost(ttl_trip_cost_per_prod, kit_dist_config, vehicle_id, shop_orders, response)
        except Exception as e:
            response['status'] = False
            response['msg'] = e
            return response

    
    @CeleryTask(bind=True)
    @api.multi
    def cron_create_loginext_route(self, priority=None, orderRefIds=None, reference=None):
        '''Cron that trigger the loginext route planning process.'''
        _ln_req = {}
        order_references = []
        self.env = self
        loginext_conf_obj = self.env['koko.loginext.conf'].sudo().search([], limit=1)
        koko_sd_obj  = self.env['koko.sd.trip'].sudo()
        if priority == None:
            loginext_conf_obj.trip_count = 0
            loginext_conf_obj.current_priority = 'PRIORITY1'
            priority = 'PRIORITY1'
        _ln_req['routeName'] = str(priority) + '-TRIP-' + str(datetime.now().strftime('%s'))
        _ln_req["deliveryMediumStartLocation"] = loginext_conf_obj.loginext_branch_name
        _ln_req["territoryProfile"] = "Default"

        del_associate_ids = self.env['koko.dist.vehicle.config'].search([('is_consumed','=',False)])
        del_medium_ref_ids = [rec.delivery_medium_ref_id for rec in del_associate_ids if rec.delivery_medium_ref_id != False]
        if not del_medium_ref_ids:
            logger.info('Unplanned delivery associates not avaliable.')
            return True
        _ln_req["deliveryMediumReferenceIds"] = del_medium_ref_ids

        if orderRefIds == None:
            # search PRIORITY1 order here
            orderRefIds = self.env['koko.sd.trip.shop.details'].search([('ln_priority','=','PRIORITY1'), ('state','=','draft')])
            for i in orderRefIds:
                if i.ln_order_ref_id:
                    order_references.append(i.ln_order_ref_id)
                elif i.ln_pickup_order_ref_id:
                    order_references.append(i.ln_pickup_order_ref_id)
        else:
            new_orders = self.env['koko.sd.trip.shop.details'].search([('ln_priority','=',priority), ('state','=','draft')])
            new_orders = [ii.id for ii in new_orders]
            orderRefIds.extend(new_orders)
            logger.info('==========%s'%(orderRefIds))      
            for item in orderRefIds:
                obj = self.env['koko.sd.trip.shop.details'].browse(item)
                if obj.ln_order_ref_id:
                    if obj.ln_order_ref_id not in order_references:
                        order_references.append(obj.ln_order_ref_id)
                elif obj.ln_pickup_order_ref_id:
                    if obj.ln_pickup_order_ref_id not in order_references:
                        order_references.append(obj.ln_pickup_order_ref_id)

            if reference != None:
                order_references.extend(reference)
                order_references = list(set(order_references))

        _ln_req['orderReferenceIds'] = order_references
        logger.info('============ ORDER-REQUEST ================= \n %s' % (_ln_req))

        api_token_obj = self.env['koko.loginext.conf'].sudo().search([], limit=1)
        if not api_token_obj:
            raise UserError('API Token Not Configured.')   
        headers = {
            'Content-Type': 'application/json',
            'WWW-Authenticate': api_token_obj.loginext_api_token
        }
        url = 'https://api.loginextsolutions.com/TripApp/v1/plan'
        # url = 'https://api.loginextsolutions.com/TripApp/mile/v1/plan'
        res = requests.post(url, headers=headers, json=_ln_req)
        logger.info('============ ORDER-PLANNING-REQ ================= \n %s \n' % (res.content.decode('utf-8')))
        return res

    def get_order_ref_ids(self, orders):
        ''' This function is used to get orders pickup and deliver ref id.'''
        ids = []
        for obj in orders:
            if obj.ln_pickup_order_ref_id:
                ids.append(obj.ln_pickup_order_ref_id)
            if obj.ln_order_ref_id:
                ids.append(obj.ln_order_ref_id)

    @CeleryTask(bind=True)
    @api.multi
    def update_end_trip_status_in_ln(self, date):
        ''' This function is used to update the trip status in loginext.'''
        self.env = self
        trip_obj = self.env['koko.sd.trip']
        order_obj = self.env['koko.sd.trip.shop.details']
        end_trips = trip_obj.search([('ln_trip_ref_id','!=',False),('scheduled_date','=', date), ('state', 'in' ,['done', 'cancelled'])])
        logger.info(end_trips)
        data = []
        for trip in end_trips:
            stop_trip_data = {}
            stop_trip_data['tripReferenceId'] = trip.ln_trip_ref_id
            completed_orders = order_obj.search([('koko_sd_trip_id','=',trip.id),('state','=','completed')])
            cancelled_orders = order_obj.search([('koko_sd_trip_id','=',trip.id),('state','=','cancelled')])
            if cancelled_orders:
                stop_trip_data['notDispatchedOrders'] = trip_obj.get_order_ref_ids(cancelled_orders)
            if completed_orders:
                stop_trip_data['deliveredOrders'] = trip_obj.get_order_ref_ids(completed_orders)
            data.append(stop_trip_data)
        logger.info(data)
        if data:
            url = config.get('trip_stop_api')
            responce = self.env['koko.loginext.conf'].sendRequestToLoginext(url, data)