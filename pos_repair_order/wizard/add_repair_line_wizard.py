# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)

class AddItemWizard(models.TransientModel):
    _name = 'add.item.repair.line.wizard'
    _description = 'Add Item Wizard'

    # attributes
    product_uom_qty = fields.Float('Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    qty_on_hand = fields.Float("Qty On Hand", compute="_compute_qty",  readonly=True, default=0)
    available_to_sell = fields.Float("Available To Sell", compute="_compute_product_qty_to_sell", readonly=True, default=0)
    forecasted_qty = fields.Float("Forecasted Qty", compute="_compute_qty",  readonly=True, default=0)
    unit_price = fields.Float("Price", related="product_id.lst_price",  readonly=True)

    # relations
    product_id = fields.Many2one("product.product", string="Product", required=True)
    repair_id = fields.Many2one("repair.order")
    pr_uom_id = fields.Many2one('uom.uom', 'UOM', related='product_id.uom_id')

    @api.depends('product_id')    
    def _compute_qty(self):
        """
        This function compute on hand quantity and forcasted quantity of product.
        """
        for rec in self:
            if rec.product_id:
                res = self.env['product.product'].search([('id', '=', rec.product_id.id)])._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'), self._context.get('from_date'), self._context.get('to_date'))
                if res:
                    rec.qty_on_hand = res[rec.product_id.id]['qty_available']
                    rec.forecasted_qty = res[rec.product_id.id]['virtual_available']
                    # rec.available_to_sell = res[rec.product_id.id]['qty_available'] - res[rec.product_id.id]['outgoing_qty']
            else:
                rec.qty_on_hand = 0
                rec.forecasted_qty = 0
                # rec.available_to_sell = 0

    @api.depends('product_id', 'product_id.qty_available',
                 'product_id.outgoing_qty')
    def _compute_product_qty_to_sell(self):
        """
            Returns the available products to Sell.
        """
        for rec in self:
            context = dict(rec._context)
            # Updating context
            context.update({
                'warehouse': rec.repair_id.warehouse_id.id,
                'location': rec.repair_id.warehouse_id.repair_operation_type.default_location_src_id.id})
            # Get Availability of product
            res_loc = self.env['product.product'].search([
                ('id', '=', rec.product_id.id)
            ]).with_context({
                'location':
                rec.repair_id.warehouse_id.repair_operation_type.default_location_src_id.id
            })._compute_quantities_dict(
                self._context.get('lot_id'), self._context.get('owner_id'),
                self._context.get('package_id'), self._context.get('from_date'),
                self._context.get('to_date'))
            _logger.info('========res_loc=======res_loc==== %s' % (res_loc))
            res = rec.product_id.with_context(**context)._product_available()
            _logger.info('=====Res====_compute_product_qty_to_sell====: %s' % (res))
            # Quantity on hand
            qty_available = res_loc[rec.product_id.id]['qty_available'] if \
                rec.product_id.id in res_loc else 0
            # Get Reserved Qty
            reserved_qty = res_loc[rec.product_id.id]['outgoing_qty'] if \
                rec.product_id.id in res_loc else 0
            # Update Available to Sell
            rec.available_to_sell = qty_available - reserved_qty


    def prepare_move_dict(self, product, move_dict, qty):
        """
        This method prepare data for stock.picking and stock.move if
        a tag along product is added.
        """
        for tag in product.tag_along_product_pack:
            if tag.product_id.type in ['consu', 'product']:
                if tag.product_id.id in move_dict:
                    move_dict[tag.product_id.id] += qty * tag.product_quantity
                else:
                    move_dict[tag.product_id.id] = qty * tag.product_quantity
                self.prepare_move_dict(tag.product_id, move_dict, qty)
            else:
                self.prepare_move_dict(tag.product_id, move_dict, qty)
        print(move_dict)
        return move_dict

    def add_item_to_repair_order(self):
        """
        This function add line in either repair.line or repair.fee depending on the type of product.
        """
        for rec in self:
            obj = None
            if rec.product_id.type in ['consu', 'product']:
                obj = 'repair.line'
            elif rec.product_id.type in ['service']:
                obj = 'repair.fee'
            if obj:
                line_rec = self.env[obj].sudo().create({
                    'repair_id': rec.repair_id.id,
                    'product_id': rec.product_id.id,
                    'product_uom_qty': rec.product_uom_qty,
                    'price_unit': rec.unit_price,
                    'product_uom': rec.pr_uom_id.id,
                    **({'location_id': rec.repair_id.warehouse_id.repair_operation_type.default_location_src_id.id} if obj in ['repair.line'] else {}),
                    **({'location_dest_id': rec.repair_id.warehouse_id.repair_operation_type.default_location_dest_id.id} if obj in ['repair.line'] else {}),
                    **({'name': rec.product_id.name} if obj in ['repair.fee'] else {})
                })
                line_rec.onchange_product_id()
                move_dict = {}
                move_dict = self.prepare_move_dict(rec.product_id, move_dict, line_rec.product_uom_qty)    
                picking_rec = None
                if move_dict or rec.product_id.type in ['consu', 'product']:
                    picking_type_id = rec.repair_id.warehouse_id.repair_operation_type
                    picking_rec = self.env['stock.picking'].sudo().create({
                        **({'partner_id': rec.repair_id.partner_id.id} if rec.repair_id.partner_id.id else {}),
                        'picking_type_id': picking_type_id.id,
                        'location_id': picking_type_id.default_location_src_id.id,
                        'location_dest_id': picking_type_id.default_location_dest_id.id,
                        'origin': 'Stock Picking for '+ rec.repair_id.name,
                        'repair_obj_id': rec.repair_id.id
                    })
                if rec.product_id.type in ['consu', 'product']:
                    move_rec = self.env['stock.move'].sudo().create({
                        'picking_id': picking_rec.id,
                        'product_id': line_rec.product_id.id,
                        'product_uom_qty': line_rec.product_uom_qty,
                        'product_uom': line_rec.product_uom.id,
                        'location_id': rec.repair_id.warehouse_id.repair_operation_type.default_location_src_id.id,
                        'location_dest_id': rec.repair_id.warehouse_id.repair_operation_type.default_location_dest_id.id,
                        'name': rec.repair_id.name
                    })
                    line_rec.move_id = move_rec.id
                for item in move_dict:
                    product = self.env['product.product'].sudo().search([('id', '=', int(item))])
                    self.env['stock.move'].sudo().create({
                        'picking_id': picking_rec.id,
                        'product_id': product.id,
                        'product_uom_qty': move_dict[item],
                        'product_uom': product.product_tmpl_id.uom_id.id,
                        'location_id': rec.repair_id.warehouse_id.repair_operation_type.default_location_src_id.id,
                        'location_dest_id': rec.repair_id.warehouse_id.repair_operation_type.default_location_dest_id.id,
                        'name': rec.repair_id.name
                    })
                if picking_rec:
                    rec.repair_id.stock_picking_id = [(4, picking_rec.id, None)]
                    picking_rec.action_confirm()
                    picking_rec.action_assign()
                    if rec.repair_id.session_id.config_id.ro_stock_transfer:
                        picking_rec.button_validate()