# -*- coding: utf-8 -*-

try:
   import newrelic
   import newrelic.agent
except:
   newrelic = None

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    repair_obj_id = fields.Many2one("repair.order", string="Repair Order")

    def create_picking_for_repair_order(self, repair_id):
        """
        This function created stock.picking and stock.picking.line for a specific repair.order.
        """
        newrelic.agent.set_transaction_name("create_picking_for_repair_order_pro", "/StockPicking", priority=None)
        if not repair_id.warehouse_id.repair_operation_type:
            raise UserError('Picking type is not exist in repair.order record.')
        if not repair_id.stock_picking_id and repair_id.operations:
            picking_type_id = repair_id.warehouse_id.repair_operation_type
            rec = self.sudo().create({
                **({'partner_id': repair_id.partner_id.id} if repair_id.partner_id.id else {}),
                'picking_type_id': picking_type_id.id,
                'location_id': picking_type_id.default_location_src_id.id,
                'location_dest_id': picking_type_id.default_location_dest_id.id,
                'origin': 'Stock Picking for ' + repair_id.name,
                'repair_obj_id': repair_id.id
            })
            repair_id.stock_picking_id = [(6, 0, [rec.id])]
            for line in repair_id.operations:
                move_rec = self.env['stock.move'].sudo().create({
                    'picking_id': rec.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    # 'quantity_done': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'location_id': picking_type_id.default_location_src_id.id,
                    'location_dest_id': picking_type_id.default_location_dest_id.id,
                    'name': repair_id.name
                })
                line.move_id = move_rec
            rec.action_confirm()
            rec.action_assign()
            for ii in rec.move_ids_without_package:
                if ii.state not in ['assigned']:
                    rec.do_unreserve()
                    break 
            if repair_id.session_id.config_id.ro_stock_transfer:
                rec.button_validate()
                for ii in rec.move_ids_without_package:
                    if ii.state not in ['assigned']:
                        rec.do_unreserve()
                        break 
            return True

    def create_rev_picking_for_repair_order(self, repair_obj):
        """
        This function create reverse picking for stock.picking at the time on Load quotation payment.
        """
        newrelic.agent.set_transaction_name("create_rev_picking_for_repair_order_pro", "/StockPicking", priority=None)
        return_picking_type_id = self.picking_type_id.return_picking_type_id
        if return_picking_type_id and repair_obj.operations:
            rev_rec = self.sudo().create({
                **({'partner_id': repair_obj.partner_id.id} if repair_obj.partner_id.id else {}),
                'picking_type_id': return_picking_type_id.id,
                'location_id': return_picking_type_id.default_location_src_id.id,
                'location_dest_id': return_picking_type_id.default_location_dest_id.id,
                'origin': 'Reverse Stock Picking for '+ repair_obj.name,
                'repair_obj_id': repair_obj.id
            })
            repair_obj.rev_stock_picking_id = rev_rec.id
            for line in repair_obj.operations:
                rev_move_rec = self.env['stock.move'].sudo().create({
                    'picking_id': rev_rec.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    # 'quantity_done': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'location_id': return_picking_type_id.default_location_src_id.id,
                    'location_dest_id': return_picking_type_id.default_location_dest_id.id,
                    'name': repair_obj.name
                })
                line.rev_move_id = rev_move_rec
            rev_rec.action_confirm()
            rev_rec.action_assign() 
            for ii in rev_rec.move_ids_without_package:
                if ii.state not in ['assigned']:
                    rev_rec.do_unreserve()
                    break
            if repair_obj.session_id.config_id.ro_stock_transfer:
                rev_rec.button_validate()          
                for ii in rev_rec.move_ids_without_package:
                    if ii.state not in ['assigned']:
                        rev_rec.do_unreserve()
                        break 
            return True

    def auto_repair_order_transfer_picking(self, repair_obj, op_type_obj):
        """
        """
        newrelic.agent.set_transaction_name("auto_repair_order_transfer_picking_pro", "/StockPicking", priority=None)
        if repair_obj.operations:
            picking_rec = self.sudo().create({
                **({'partner_id': repair_obj.partner_id.id} if repair_obj.partner_id.id else {}),
                'picking_type_id': op_type_obj.id,
                'location_id': op_type_obj.default_location_src_id.id,
                'location_dest_id': op_type_obj.default_location_dest_id.id,
                'origin': 'Reverse Stock Picking for '+ repair_obj.name,
                'repair_obj_id': repair_obj.id
            })
            repair_obj.rev_stock_picking_id = picking_rec.id
            for line in repair_obj.operations:
                self.env['stock.move'].sudo().create({
                    'picking_id': picking_rec.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'location_id': op_type_obj.default_location_src_id.id,
                    'location_dest_id': op_type_obj.default_location_dest_id.id,
                    'name': repair_obj.name
                })
            if repair_obj.final_pos_order_id:
                repair_obj.final_pos_order_id.picking_id = picking_rec.id
            picking_rec.action_confirm()
            picking_rec.action_assign()
            picking_rec.button_validate()           
            return True

    def create_reverse(self, repair_obj):
        newrelic.agent.set_transaction_name("create_reverse_pro", "/StockPicking", priority=None)
        return_picking_type_id = self.picking_type_id.return_picking_type_id
        if return_picking_type_id:
            vals = {
                'picking_type_id': return_picking_type_id.id,
                'origin': self.name,
                'repair_obj_id': repair_obj.id
            }
            picking_id = self.new(vals)
            picking_id.onchange_picking_type()
            for move_line in self.move_lines:
                move_id = move_line.new({'product_id': move_line.product_id.id})
                move_id.onchange_product_id()
                move_id.update({
                    'product_uom_qty': move_line.product_uom_qty,
                    'location_id': move_line.location_dest_id.id,
                    'location_dest_id': move_line.location_id.id
                })
                picking_id.move_lines += move_id
            vals = picking_id._convert_to_write(picking_id._cache)
            vals_move_lines = []
            for vals_move_line in vals['move_lines']:
                if vals_move_line[0] == 0:
                    vals_move_lines.append(vals_move_line)
            vals['move_lines'] = vals_move_lines
            picking_id = self.create(vals)
            picking_id.action_confirm()
            picking_id.action_assign()
            for ii in picking_id.move_ids_without_package:
                if ii.state not in ['assigned']:
                    picking_id.do_unreserve()
                    break
            if repair_obj.warehouse_id.transfer_stock_on_rrot:
                picking_id.button_validate()
                for ii in picking_id.move_ids_without_package:
                    if ii.state not in ['assigned']:
                        picking_id.do_unreserve()
                        break
            return picking_id

    @api.model_create_multi
    def create(self, vals_list):
        res = super(StockPicking, self).create(vals_list)
        for rec in res:
            if rec.backorder_id and rec.repair_obj_id:
                if rec.repair_obj_id.back_order_ids:
                    rec.repair_obj_id.back_order_ids = [(4, rec.id)]
                else:
                    rec.repair_obj_id.back_order_ids = [(6, 0, [rec.id])]
        return res



    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        newrelic.agent.set_transaction_name("action_assign_pro", "/StockPicking", priority=None)
        self.filtered(lambda picking: picking.state == 'draft').action_confirm()
        moves = self.mapped('move_lines').filtered(lambda move: move.state not in ('draft', 'cancel', 'done'))
        if not moves:
            raise UserError(_('Nothing to check the availability for.'))
        move_count = len(moves.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']))
        new_count = 0
        for move in moves.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
            reserved_availability = {move: move.reserved_availability for move in moves}
            missing_reserved_uom_quantity = move.product_uom_qty - reserved_availability[move]
            missing_reserved_quantity = move.product_uom._compute_quantity(missing_reserved_uom_quantity, move.product_id.uom_id, rounding_method='HALF-UP')
            need = missing_reserved_quantity
            forced_package_id = move.package_level_id.package_id or None
            available_quantity = self.env['stock.quant']._get_available_quantity(move.product_id, move.location_id, package_id=forced_package_id)
            if need <= available_quantity:
                new_count += 1
        # If a package level is done when confirmed its location can be different than where it will be reserved.
        # So we remove the move lines created when confirmed to set quantity done to the new reserved ones.
        if new_count == move_count:
            package_level_done = self.mapped('package_level_ids').filtered(lambda pl: pl.is_done and pl.state == 'confirmed')
            package_level_done.write({'is_done': False})
            moves._action_assign()
            package_level_done.write({'is_done': True})
            return True
        return False