# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class RemoveItemWizard(models.TransientModel):
    _name = 'remove.item.repair.line.wizard'
    _description = 'Remove Item Wizard'

    # relations
    repair_id = fields.Many2one("repair.order")
    removing_line_ids = fields.One2many("remove.item.line", "remove_item_repair_id", string = "Removing Lines")

    def update_waiting_moves(self, product_moves, removing_qty):
        """
        This method update stock move that are in waiting state.
        """
        for product_move in product_moves:
            if removing_qty > 0 and product_move.state not in ['done', 'cancel', 'assigned'] and product_move.product_uom_qty > 0:
                if product_move.product_uom_qty >= removing_qty:
                    product_move.product_uom_qty = product_move.product_uom_qty - removing_qty
                    removing_qty = product_move.product_uom_qty - removing_qty
                else:
                    removing_qty = removing_qty - product_move.product_uom_qty
                    product_move.product_uom_qty = 0
        return product_moves, removing_qty

    def update_assigned_moves(self, product_moves, removing_qty):
        """
        This method update stock move that are in assigned state.
        """
        for product_move in product_moves:
            if removing_qty > 0 and product_move.state in ['assigned'] and product_move.product_uom_qty > 0:
                product_move.picking_id.do_unreserve()
                if product_move.product_uom_qty >= removing_qty:
                    product_move.product_uom_qty = product_move.product_uom_qty - removing_qty
                    removing_qty = product_move.product_uom_qty - removing_qty
                else:
                    removing_qty = removing_qty - product_move.product_uom_qty
                    product_move.product_uom_qty = 0
                product_move.picking_id.action_assign()
        return product_moves, removing_qty

    def update_done_moves(self, product_moves, removing_qty, rev_rec):
        """
        This methis update stock move that are in done state.
        """
        return_picking_type_id = self.repair_id.warehouse_id.repair_operation_type.return_picking_type_id
        for product_move in product_moves:
            if removing_qty > 0 and product_move.state in ['done']:
                if not rev_rec:
                    rev_rec = self.env['stock.picking'].sudo().create({
                        **({'partner_id': self.repair_id.partner_id.id} if self.repair_id.partner_id.id else {}),
                        'picking_type_id': return_picking_type_id.id,
                        'location_id': return_picking_type_id.default_location_src_id.id,
                        'location_dest_id': return_picking_type_id.default_location_dest_id.id,
                        'origin': 'Remove Stock Picking for '+ self.repair_id.name,
                        'repair_obj_id': self.repair_id.id
                    })
                if product_move.product_uom_qty >= removing_qty:
                    stock_move_data = {
                        'product_id': product_move.product_id.id,
                        'product_uom_qty': removing_qty,
                        'product_uom': product_move.product_uom.id,
                        'location_id': return_picking_type_id.default_location_src_id.id,
                        'location_dest_id': return_picking_type_id.default_location_dest_id.id,
                        'name': self.repair_id.name
                    }
                    stock_move_data['picking_id'] = rev_rec.id
                    self.env['stock.move'].sudo().create(stock_move_data)
                    self.repair_id.remove_stock_picking_id = [(4, rev_rec.id, None)]
                    removing_qty = product_move.product_uom_qty - removing_qty
                else:
                    stock_move_data = {
                        'product_id': product_move.product_id.id,
                        'product_uom_qty': 0,
                        'product_uom': product_move.product_uom.id,
                        'location_id': return_picking_type_id.default_location_src_id.id,
                        'location_dest_id': return_picking_type_id.default_location_dest_id.id,
                        'name': self.repair_id.name
                    }
                    stock_move_data['picking_id'] = rev_rec.id
                    self.env['stock.move'].sudo().create(stock_move_data)
                    self.repair_id.remove_stock_picking_id = [(4, rev_rec.id, None)]
                    removing_qty = removing_qty - product_move.product_uom_qty
        return product_moves, removing_qty, rev_rec


    def remove_lines(self, removing_line_ids):
        """
        This method remove line from `repair.order` or `repair.fee`.
        """
        for line in removing_line_ids:
            if line.remove_qty > 0:
                line_rec = self.env[line.line_obj].sudo().search([('id','=',int(line.line_id))])
                if line.remove_qty == line_rec.product_uom_qty:
                    self.env['remove.repair.line'].sudo().create({
                        'product_id': line_rec.product_id.id,
                        'removed_qty': line.remove_qty,
                        'remove_reason': line.remove_reason,
                        'repair_order_id': self.repair_id.id,
                        'user_id': self.env.user.id,
                        'timestamp': datetime.now()
                    })
                    line_rec.unlink()
                elif line.remove_qty < line_rec.product_uom_qty:
                    self.env['remove.repair.line'].sudo().create({
                        'product_id': line_rec.product_id.id,
                        'removed_qty': line.remove_qty,
                        'remove_reason': line.remove_reason,
                        'repair_order_id': self.repair_id.id,
                        'user_id': self.env.user.id,
                        'timestamp': datetime.now()
                    })
                    line_rec.product_uom_qty = line_rec.product_uom_qty - line.remove_qty


    def remove_item_to_repair_order(self):
        """
        This method remove line from `repair.order`, `repair.fee` and
        update stock moves.
        """
        temp = []
        for line in self.removing_line_ids:
            if line.remove_qty > 0:
                line_rec = self.env[line.line_obj].sudo().search([('id','=',int(line.line_id))])
                if line_rec.product_id.type in ['consu', 'product']:
                    temp.append(line_rec.product_id.id)
        if temp:
            rev_rec = None
            moves = self.env['stock.move']
            for picking in self.repair_id.stock_picking_id:
                for move in picking.move_ids_without_package:
                    moves |= move
            for line in self.removing_line_ids:
                product_moves = self.env['stock.move']
                removing_qty = line.remove_qty
                if line.remove_qty > 0 and line.product_id.type in ['consu', 'product']:
                    for move in moves:
                        if move.product_id.id == line.product_id.id:
                            product_moves |= move
                product_moves, removing_qty = self.update_waiting_moves(product_moves,removing_qty)
                product_moves, removing_qty = self.update_assigned_moves(product_moves,removing_qty)
                product_moves, removing_qty, rev_rec = self.update_done_moves(product_moves,removing_qty, rev_rec)
            if rev_rec:
                rev_rec.action_confirm()
                rev_rec.action_assign()
                if self.repair_id.session_id.config_id.ro_stock_transfer:
                    rev_rec.button_validate()
            self.remove_lines(self.removing_line_ids)

class RemoveItemLine(models.TransientModel):
    _name = 'remove.item.line'
    _description = 'Remove Item Line'

    # attributes
    remove_qty = fields.Float('Remove Quantity')
    unit_price = fields.Float('Unit Price')
    product_uom_qty = fields.Float('Quantity')
    remove_reason = fields.Char('Reason to Remove')
    line_id = fields.Integer('Line ID')
    line_obj = fields.Char('Line Object')

    # relations
    product_id = fields.Many2one("product.product", string="Product")
    remove_item_repair_id = fields.Many2one("remove.item.repair.line.wizard")

    @api.onchange('remove_qty')
    def _onchange_remove_qty(self):
        """
        This function checks whether qty is always less than or equal to product quantity in repair order.
        """
        for rec in self:
            if rec.remove_qty > rec.product_uom_qty:
                raise UserError('Remove Quantity is not greater then Product Quantity in Line')
