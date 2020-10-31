# -*- coding: utf-8 -*-

import odoo
from odoo import http
from odoo.http import request
from odoo.http import Response
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError
import werkzeug.wrappers
import base64
import os
import logging
import requests
import json
import time
from odoo.addons.koko_hr_employee_login.helper.utility import *

logger = logging.getLogger(__name__)


class LoginextAPI(odoo.http.Controller):

    def get_trip_time(self, st, et):
        '''Calculate trip total traveling time.'''
        st_time = datetime.strptime(st, '%Y-%m-%d %H:%M:%S')
        et_time = datetime.strptime(et, '%Y-%m-%d %H:%M:%S')
        total_diff = et_time - st_time
        in_hour = divmod(total_diff.days * 86400 + total_diff.seconds, 60)
        ts = (in_hour[0]*60+in_hour[1])/3600
        return ts

    def get_next_priority(self, priority):
        '''check next priority to the given one.'''
        priority_num = int(priority[-1])
        if priority_num == 5:
            return False
        nxt_priority = 'PRIORITY'+str(priority_num+1)
        model_shop_detail = request.env['koko.sd.trip.shop.details'].sudo()
        new_orders_ids = model_shop_detail.search([('ln_priority','=',nxt_priority)])
        if not new_orders_ids:
            self.get_next_priority(nxt_priority)
        api_token_obj = request.env['koko.loginext.conf'].sudo().search([], limit=1)
        api_token_obj.current_priority = nxt_priority
        return nxt_priority
    
    def order_unassign_from_trip(self, orderList):
        url = 'https://api.loginextsolutions.com/ShipmentApp/mile/v1/manual/unassign?referenceId=%s'
        api_token_obj = request.env['koko.loginext.conf'].sudo().search([], limit=1)
        if not api_token_obj:
            raise UserError('API Token Not Configured.')   
        headers = {
            'Content-Type': 'application/json',
            'WWW-Authenticate': api_token_obj.loginext_api_token
        }
        for order in orderList:
            req = url % (order)
            res = requests.put(req, headers=headers)
            logger.info(res.content)
        logger.info('============= Order-Unassigned ============= \n %s \n' % (len(orderList)))

    def sync_sale_order(self, new_priority, delivery_date, unassignedOrdersIds):
        '''Function sync all the new priority order before calling route planning api.'''

        model_sd_trip = request.env['koko.sd.trip'].sudo()
        model_shop_detail = request.env['koko.sd.trip.shop.details'].sudo()
        new_orders_ids = model_shop_detail.search([('ln_priority','=',new_priority)])
        model_sd_trip.update_delivery_date(new_orders_ids, delivery_date)
        # order to sync at loginext end
        create_del_order_ids = model_shop_detail.search([
            ('ln_order_ref_id','=',False),
            ('state','=','draft'),
            ('shop_id','!=',False),
            ('ln_priority','=',new_priority),
            ('shop_id.ln_customer_reference_id', '!=', False)])
        create_pkp_order_ids = new_orders_ids.search([
            ('ln_pickup_order_ref_id','=',False),
            ('state','=','draft'),
            ('ln_priority','=',new_priority),
            ('excess_unloaded_serial_ids', '!=', False),
            ('shop_id','!=',False),
            ('shop_id.ln_customer_reference_id', '!=', False),
            ('check_date','=', False),
            ('return_location', '=', True)])
        logger.info('\n=== Create-Delivery-Orders === : %s \n' % (len(create_del_order_ids)))
        logger.info('\n=== Create-Pickup-Orders === : %s \n' % (len(create_pkp_order_ids)))

        delivery_orders = model_shop_detail.create_del_orders_in_chunk(create_del_order_ids)
        pickup_orders = model_shop_detail.create_pkp_orders_in_chunk(create_pkp_order_ids)
        delivery_orders.extend(pickup_orders)
        # update the delivery date in rest of the orders
        del_updated_order_ids = [d.id for d in new_orders_ids if d.id not in [i.id for i in create_del_order_ids]]
        pkp_updated_order_ids = [d.id for d in new_orders_ids if d.id not in [i.id for i in create_pkp_order_ids]]
        del_updated_order_ids.extend(pkp_updated_order_ids)
        update_order_ids = model_shop_detail.search([('id','in',del_updated_order_ids),('ln_priority','=',new_priority)])
        logger.info('\n========== Update-Orders-crate ============== \n %s \n' % (len(update_order_ids)))
        model_shop_detail.update_orders_in_chunk(update_order_ids)
        model_shop_detail.update_orders_crates_in_chunk(update_order_ids)
        unassigned_orders = [unassignedOrdersIds]
        unassigned_orders.extend(new_orders_ids)
        unassigned_orders = [ii.id for o in unassigned_orders for ii in o]
        logger.info('\n ====== Calling Route Panning API ===== \n')
        logger.info('\n ====== %s: %s ===== \n' % (new_priority, len(unassigned_orders)))
        
        return unassigned_orders, delivery_orders

    def get_loginext_route_cost(self, ref_id, routename):
        '''Function call the trip information api for finding cost, time & distance.'''

        api_token_obj = request.env['koko.loginext.conf'].sudo().search([], limit=1)
        if not api_token_obj:
            raise UserError('API Token Not Configured.')   
        headers = {
            'Content-Type': 'application/json',
            'WWW-Authenticate': api_token_obj.loginext_api_token
        }
        url = 'https://api.loginextsolutions.com/TripApp/mile/v1/trip/get?referenceId=%s&tripname=%s' % (ref_id, routename)
        _get_trip_res = requests.get(url, headers=headers)
        _get_trip_res = _get_trip_res.json()['data']
        return _get_trip_res

    @http.route('/api/v1/optimised/trip/get', methods=['POST'], type='json', auth='public', website=True, csrf=False)
    def get_planned_route(self, **post):
        '''Accept response from route planning API and create trip.'''

        model_sd_trip = request.env['koko.sd.trip'].sudo()
        model_shop_detail = request.env['koko.sd.trip.shop.details'].sudo()
        response = request.jsonrequest
        logger.info('\n  === Route Planning Response: %s === \n', (datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        logger.info('\n\n  === %s === \n\n' % (response))
        # Un-assigned orders
        route_name = response['routeName'] 
        priority = route_name.split('-')[0]
        api_token_obj = request.env['koko.loginext.conf'].sudo().search([], limit=1)
        if api_token_obj.current_priority == priority:
            unassignedOrders = []
            for i in response['unassignmentReasons']:
                unassignedOrders.extend(i['orderReferenceIds'])
            unassignedOrdersIds = model_shop_detail.search(['|', ('ln_order_ref_id','in',unassignedOrders), ('ln_pickup_order_ref_id','in',unassignedOrders)])

            new_priority = self.get_next_priority(priority) # get new priority
            model_sd_trip.set_priority(new_priority)
            trip_date = date.today() + timedelta(days=1)
            delivery_date = trip_date.strftime('%Y-%m-%d')
            trips = response.get('notificationDetails', False)
            if trips:
                for trip_info in trips:
                    delMediumName = trip_info['deliveryMediumName']
                    # assigned orders
                    assignedOrders = []
                    sorted_orders = sorted(trip_info['orderDetails'], key=lambda k: k['deliveryOrder'])
                    logger.info("Sorted Order List: %s" % sorted_orders)
                    order_ids = []
                    for odr in sorted_orders:
                        assignedOrders.append(odr['orderNo'])
                    assignedOrders = model_sd_trip.get_ref_by_order_name(assignedOrders)
                    # check trip cost
                    _get_trip_res = self.get_loginext_route_cost(trip_info['referenceId'],response['routeName'])
                    order_Ids = model_shop_detail.search(['|', ('ln_order_ref_id','in',assignedOrders), ('ln_pickup_order_ref_id','in',assignedOrders)])
                    if 'totalPlannedTime' in _get_trip_res and 'totalPlannedDistance' in _get_trip_res:
                        value = {
                            'delivery_medium_name': delMediumName,
                            'orders': order_Ids,
                            'trip_time': float(float(_get_trip_res['totalPlannedTime'])/60),
                            'trip_km': _get_trip_res['totalPlannedDistance']
                        }
                        check_cost = model_sd_trip.get_trip_cost(value)
                        if check_cost['status']:
                            for odr in sorted_orders:
                                oid = odr['orderNo'].split('-')[1]
                                model_sd_trip.set_sequence(oid, odr['deliveryOrder'])
                            model_sd_trip.create_trip(delMediumName, order_Ids, delivery_date, trip_info['referenceId'])
                        else:
                            unassignedOrders.extend(assignedOrders)
                            self.order_unassign_from_trip(assignedOrders)
                
                is_p1_available = model_shop_detail.check_p1_orders(unassignedOrders)
                if is_p1_available and new_priority:
                    unassigned_orders, delivery_orders = self.sync_sale_order(new_priority, delivery_date, unassignedOrdersIds)
                    is_queue_empty('ln_sync_shop_order') # check orders synced 
                    is_queue_empty('ln_sync_shop_products') # check orders quantity updated
                    time.sleep(2*60) # sleep for 2 minutes
                    model_sd_trip.cron_create_loginext_route(new_priority, unassigned_orders, unassignedOrders)
                    return werkzeug.wrappers.Response(status=202)
                else:
                    if is_p1_available:
                        tomorrow_del_dt = datetime.strptime(delivery_date, '%Y-%m-%d') +  timedelta(days=1)
                        model_sd_trip.update_P1_delivery_date(unassignedOrders, tomorrow_del_dt)
                    if api_token_obj.trip_count == 0:
                        request.env['koko.loginext.conf'].sudo().sendRoutePlanningMail()
                    logger.info('==== ALL-TRIPS-CREATED-FOR: %s ====' % (delivery_date))
                    return werkzeug.wrappers.Response(status=202)
            else:
                # if not any trip created
                if new_priority:
                    unassigned_orders, delivery_orders = self.sync_sale_order(new_priority, delivery_date, unassignedOrdersIds)
                    time.sleep(2*60) # sleep for 2 minutes
                    model_sd_trip.cron_create_loginext_route(new_priority, unassigned_orders, unassignedOrders)
                    return werkzeug.wrappers.Response(status=202)
                else:
                    if api_token_obj.trip_count == 0:
                        request.env['koko.loginext.conf'].sudo().sendRoutePlanningMail()
                    return werkzeug.wrappers.Response(status=202)
        else:
            logger.info('Already sent %s priority response' % (priority))
            return werkzeug.wrappers.Response(status=202)

    @http.route('/api/v1/delivery/associate/get', methods=['POST'], type='json', auth='public', website=True, csrf=False)
    def get_delivery_associate(self, **post):
        response = request.jsonrequest
        name = response.get('deliveryMediumName')
        medium_ref_id = response.get('referenceId')
        res = request.env['koko.sd.trip'].sudo().update_vehicle_ref_by_name(name, medium_ref_id)
        logger.info("Delivery medium reference id: %s updated." % (res))
        return werkzeug.wrappers.Response(status=202)
