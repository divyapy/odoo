# -*- coding: utf-8 -*-

from odoo import api, fields, models

class RepairOrderLine(models.Model):
    _inherit = 'repair.line'

    def create_diff_loc_picking(self, line):
        """
        This function create stock.picking if stock is deducated from another locations.
        """
        stock_loc_id = line.stock_loc_id
        for item in line.repair_id.session_id.config_id.picking_locations_ids:
            if stock_loc_id == item.src_location_id and item.warehouse_id.transit_locations_id:
                rec = self.env['stock.picking'].sudo().create({
                    **({'partner_id': line.repair_id.partner_id.id} if line.repair_id.partner_id.id else {}),
                    'picking_type_id': item.operation_type_id.id,
                    'location_id': stock_loc_id.id,
                    'location_dest_id': line.repair_id.session_id.config_id.warehouse_id.transit_locations_id.id
                })
                move_rec = self.env['stock.move'].sudo().create({
                    'picking_id': rec.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'quantity_done': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'location_id': stock_loc_id.id,
                    'location_dest_id': line.repair_id.session_id.config_id.warehouse_id.transit_locations_id.id,
                    'name': line.repair_id.name
                })
                line.repair_id.other_loc_stock_picking_id = [(4, rec.id, None)]
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