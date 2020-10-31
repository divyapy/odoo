# -*- coding: utf-8 -*-.

from odoo import models, fields, api, _
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class KokoSdTripShopDetails(models.Model):
    _inherit = "koko.sd.trip.shop.details"

    ln_update_sync = fields.Boolean(string="Update Sync", readonly=True)
    ln_status_sync = fields.Boolean(string="Status Sync", readonly=True)
    ln_order_ref_id = fields.Char(string="LogiNext Ref. ID.", readonly=True)

    def get_ln_ref_id(self, order_number):
        '''Function returns loginext reference id by it order number.'''
        shop_id = order_number.split('-')[1]
        shop_obj = self.sudo().browse(shop_id)
        return shop_obj.ln_order_ref_id

    def check_p1_orders(self, orderList):
        '''Returns True if PRIORITY1 orders present in un-assign orders.'''
        rec = self.sudo().search([('ln_priority', '=', 'PRIORITY1'), ('ln_order_ref_id', 'in', orderList)])
        if len(rec) != 0:
            return True
        return False

    def create_del_orders_in_chunk(self, orders):
        delivery_reference = []
        orders = [o.id for o in orders]
        for i in range(0, len(orders), 20):
            logger.info(orders[i:i+20])
            self.createLoginextDeliveryOrder(orders[i:i+20])
            # delivery_reference.extend(del_referene)
        return delivery_reference

    def create_pkp_orders_in_chunk(self, orders):
        pickup_reference = []
        orders = [o.id for o in orders]
        for i in range(0, len(orders), 20):
            logger.info(orders[i:i+20])
            self.createLoginextPickupOrder(orders[i:i+20])
            # pickup_reference.extend(pkp_reference)
        return pickup_reference

    def update_orders_in_chunk(self, orders):
        orders = [o.id for o in orders]
        for i in range(0, len(orders), 20):
            logger.info(orders[i:i+20])
            self.updateOrder(orders[i:i+20])

    def update_orders_crates_in_chunk(self, orders):
        orders = [o.id for o in orders]
        for i in range(0, len(orders), 20):
            logger.info(orders[i:i+20])
            self.updateDeliveryCratesAndLineItems(orders[i:i+20])

    def update_done_trip_status_in_ln(self):
        ''' This function is used to update status of completed trip.'''
        ir_cron = self.env['ir.cron'].sudo().search([('id', '=', self.env.ref('loginext_odoo_integration.loginext_status_update_for_trip').id)], limit=1)
        cron_run_date = datetime.strptime(ir_cron.nextcall, "%Y-%m-%d %H:%M:%S").date()
        logger.info(cron_run_date)
        cancelled_orders = self.env['koko.sd.trip.shop.details'].sudo().search([
            ('state', 'in', ['cancelled']),
            ('ln_status_sync','=', True),
            ('delivery_date', '=', cron_run_date)
        ])
        cancelled_orders = [o.id for o in cancelled_orders]
        logger.info(cancelled_orders)
        completed_orders = self.env['koko.sd.trip.shop.details'].sudo().search([
                ('state', 'in', ['completed']),
                ('ln_status_sync','=', True),
                ('delivery_date', '=', cron_run_date)
            ])
        logger.info(completed_orders)
        chunk_size = 20
        completed_orders = [o.id for o in completed_orders]
        if completed_orders:
            for i in range(0, len(completed_orders), chunk_size):
                logger.info(completed_orders[i:i + chunk_size])
                self.updateOrderStatus(completed_orders[i:i + chunk_size], "DELIVERED")
        if cancelled_orders:
            for i in range(0, len(cancelled_orders), chunk_size):
                logger.info(cancelled_orders[i:i + chunk_size])
                self.updateOrderStatus(cancelled_orders[i:i + chunk_size],"NOTDELIVERED")
        self.env['koko.sd.trip'].update_end_trip_status_in_ln(cron_run_date)