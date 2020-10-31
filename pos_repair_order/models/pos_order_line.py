# -*- coding: utf-8 -*-

from odoo import api, fields, models

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def create_picking_of_another_location(self, line):
        """
        This function create stock.picking if stock is deducated from another locations.
        """
        stock_loc_id = line.stock_location_id
        for item in line.order_id.session_id.config_id.picking_locations_ids:
            if stock_loc_id == item.src_location_id and item.warehouse_id.transit_locations_id:
                rec = self.env['stock.picking'].sudo().create({
                    **({'partner_id': line.order_id.session_id.config_id.warehouse_id.partner_id.id} if line.order_id.session_id.config_id.warehouse_id.partner_id.id else {}),
                    'picking_type_id': item.operation_type_id.id,
                    'location_id': stock_loc_id.id,
                    'location_dest_id': line.order_id.session_id.config_id.warehouse_id.transit_locations_id.id
                })
                move_rec = self.env['stock.move'].sudo().create({
                    'picking_id': rec.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty,
                    # 'quantity_done': line.qty,
                    'product_uom': line.product_id.uom_id.id,
                    'location_id': stock_loc_id.id,
                    'location_dest_id': line.order_id.session_id.config_id.warehouse_id.transit_locations_id.id,
                    'name': line.order_id.name
                })
                rec.action_confirm()
                rec.action_assign()
                for ii in rec.move_ids_without_package:
                    if ii.state not in ['assigned']:
                        rec.do_unreserve()
                        break
                if item.validate_stock:
                    rec.button_validate() 
                    for ii in rec.move_ids_without_package:
                        if ii.state not in ['assigned']:
                            rec.do_unreserve()
                            break

    @api.model_create_multi
    def create(self, vals_list):    
        res = super(PosOrderLine, self).create(vals_list)
        for line in res:
            # if not line.order_id.session_id.config_id.related_picking_in_open_state:
            print(line, '==========')
            print(line.stock_location_id, '===============stock_location_id')
            if line.stock_location_id:
                self.create_picking_of_another_location(line)
        return res