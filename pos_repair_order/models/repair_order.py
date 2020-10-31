# -*- coding: utf-8 -*-

try:
   import newrelic
   import newrelic.agent
except:
   newrelic = None

from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import logging

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'
    quotation_id = fields.Many2one("repair.order", string="Related Quotation")
    repair_id = fields.Many2one("repair.order", string="Repair Order")
    created_for = fields.Selection([('ad_pymt', 'Ad Pymt'),('normal', 'Normal')], 'Created For', default='normal')

    @api.model
    def _order_fields(self, ui_order):
        fields_return = super(PosOrder, self)._order_fields(ui_order)
        fields_return.update({'quotation_id': ui_order.get('quotation_id', '')})
        fields_return.update({'repair_id': ui_order.get('repair_id', '')})
        fields_return.update({'created_for': ui_order.get('created_for', '')})
        return fields_return

    @api.model_create_multi
    def create(self, vals_list):
        newrelic.agent.set_transaction_name("_create_pos_repair_order", "/PosOrder", priority=None)
        records = super(PosOrder, self).create(vals_list)
        for rec in records:
            print(rec, rec.repair_id, rec.created_for, '===========created_for===')
            if rec.repair_id and rec.created_for == 'ad_pymt':
                rec.repair_id.pos_order_id = rec.id
            if rec.repair_id and not rec.created_for:
                rec.repair_id.final_pos_order_id = rec.id
                if rec.repair_id.rev_stock_picking_id:
                    rec.repair_id.final_pos_order_id.picking_id = rec.repair_id.rev_stock_picking_id
        return records

class RepairOrderLine(models.Model):
    _inherit = 'repair.line'

    # attributes
    name = fields.Char("Line", default="Quotation Line")
    price_subtotal_with_tax = fields.Float(digits=0, string='Subtotal with Tax')
    discount = fields.Float(string='Discount (%)', digits=0, default=0.0)
    type = fields.Selection([('add', 'Add'),('remove', 'Remove')], 'Type', required=True, default='add')
    qty_on_hand = fields.Float("Qty On Hand", compute="_compute_qty", readonly=True, default=0)
    forecasted_qty = fields.Float("Forecasted Qty", compute="_compute_qty", readonly=True, default=0)
    available_to_sell = fields.Float("Available To Sell", compute="_compute_product_qty_to_sell", readonly=True, default=0)
    created_from = fields.Selection([('pos', 'POS'),('manual', 'Manual')], 'Created From', default='manual')
    
    # relations
    # product_id = fields.Many2one('product.product', 'Product', domain=[(
    #     'sale_ok', '=', True), ('available_in_pos', '=', True)], required=True, change_default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)  
    rev_move_id = fields.Many2one('stock.move', 'Reverse Inventory Move', readonly=True)
    stock_loc_id = fields.Many2one('stock.location', 'Stock location', readonly=True)

    @api.depends('product_id')    
    def _compute_qty(self):
        newrelic.agent.set_transaction_name("_compute_qty_pos_repair_order", "/RepairOrderLine", priority=None)
        for rec in self:
            print(rec, "=========rec========", rec.id, type(rec.id))
            print(rec.product_id, '+++++++++++rec.product_id')
            if rec.product_id:
                res = self.env['product.product'].search([('id', '=', rec.product_id.id)])._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'), self._context.get('from_date'), self._context.get('to_date'))
                if res:
                    print(res, '+++++++++res')
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
        newrelic.agent.set_transaction_name("_compute_product_qty_to_sell_pos_repair_order", "/RepairOrderLine", priority=None)
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

    @api.model_create_multi
    def create(self, vals_list):
        newrelic.agent.set_transaction_name("create_pos_repair_order", "/RepairOrderLine", priority=None)
        for val in vals_list:
            repair_obj = self.env['repair.order'].search([('id', '=', int(val['repair_id']))])
            if repair_obj and repair_obj.warehouse_id:
                val['location_id'] = repair_obj.warehouse_id.repair_operation_type.default_location_src_id.id
                val['location_dest_id'] = repair_obj.warehouse_id.repair_operation_type.default_location_dest_id.id           
        res = super(RepairOrderLine, self).create(vals_list)
        for line in res:
            if line.stock_loc_id:
                self.create_diff_loc_picking(line)
        return res

    @api.onchange('product_id')
    def _onchange_product_id(self):
        newrelic.agent.set_transaction_name("_onchange_product_id_pos_repair_order", "/RepairOrderLine", priority=None)
        if self.product_id:
            if not self.repair_id.pricelist_id:
                raise UserError(
                    _('You have to select a pricelist in the sale form !\n'
                      'Please set one before choosing a product.'))
            price = self.repair_id.pricelist_id.get_product_price(
                self.product_id, self.product_uom_qty or 1.0, self.repair_id.partner_id)
            self._onchange_qty()
            self.price_unit = price
            self.tax_ids = self.product_id.taxes_id
            self.tax_ids = self.product_id.taxes_id.filtered(lambda r: not self.company_id or r.company_id == self.company_id)
            fpos = self.repair_id.fiscal_position_id
            tax_ids_after_fiscal_position = fpos.map_tax(self.tax_ids, self.product_id, self.repair_id.partner_id) if fpos else self.tax_ids
            self.price_unit = self.env['account.tax']._fix_tax_included_price_company(price, self.product_id.taxes_id, \
                tax_ids_after_fiscal_position, self.company_id)


    @api.onchange('product_uom_qty', 'price_unit', 'tax_id')
    def _onchange_qty(self):
        newrelic.agent.set_transaction_name("_onchange_qty_pos_repair_order", "/RepairOrderLine", priority=None)
        if self.product_id:
            if not self.repair_id.pricelist_id:
                raise UserError(_('You have to select a pricelist in the sale form !'))
            self.price_subtotal_with_tax = self.price_unit * self.product_uom_qty
            if self.tax_id:
                taxes = self.tax_id.compute_all(self.price_unit, self.repair_id.pricelist_id.currency_id,\
                     self.product_uom_qty, product=self.product_id, partner=False)
                self.price_subtotal_with_tax = taxes['total_included']


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    @api.model
    def order_formatLang(self,value,currency_obj=False):
        res = value
        if currency_obj and currency_obj.symbol:
            if currency_obj.position == 'after':
                res = u'%s\N{NO-BREAK SPACE}%s' % (res, currency_obj.symbol)
            elif currency_obj and currency_obj.position == 'before':
                res = u'%s\N{NO-BREAK SPACE}%s' % (currency_obj.symbol, res)
        return res
 
    # def _default_session(self):
    #     return self.env['pos.session'].search([('state', '=', 'opened'), ('user_id', '=', self.env.uid)], limit=1)

    # def _default_pricelist(self):
    #     if(self._default_session().config_id.pricelist_id):
    #         return self._default_session().config_id.pricelist_id
    #     else:
    #         return self.env['product.pricelist'].search([('currency_id', '=', self.env.user.company_id.currency_id.id)], limit=1)

    # attributes
    quotation_id = fields.Char('Quotation Identifier', readonly=True)
    date_order = fields.Datetime('Quotation Date', readonly=True, index=True)
    quotation_sent = fields.Boolean('Quotation Sent')
    odoometer_reading = fields.Char('Odoo Meter Reading')
    repair_type = fields.Selection([
        ('quote', 'Quotation'),
        ('service', 'Service Order')], 'Type', default='quote')
    operation_type = fields.Selection([
        ('deliver', 'Deliver'),
        ('pickup', 'Pickup')], 'Operation Type')
    expected_delivery_date = fields.Datetime('Expected Delivery Date')
    total_service_time = fields.Float(compute="_compute_total", string="Actual Timing", readonly="1", store=True)
    time_by_planning = fields.Float(string="Expected Timing", readonly="1")
    adv_pymt_amt = fields.Float(string="Advance Amt", related="pos_order_id.amount_total")
    picking_state = fields.Selection([
        ('waiting', 'Waiting'),
        ('done', 'Done')], string='Picking State', compute="_compute_picking_state", search='_value_search')
    # visible_buttons = fields.Boolean(string="Buttons Visibility")

    # relations
    product_id = fields.Many2one(
        'product.product', string='Product to Repair',
        readonly=True, required=True, states={'draft': [('readonly', False)]}, default=lambda self: self._get_default_product())
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    user_id = fields.Many2one('res.users', 'Salesman')
    planning_start_time = fields.Datetime(related="planning_id.start_datetime", string="Planning Start Time")
    # pricelist_id = fields.Many2one(
    #     'product.pricelist', 'Pricelist', required=True,default=_default_pricelist)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist',help='Pricelist of the selected partner.')
    session_id = fields.Many2one(
        'pos.session', 'POS Session', index=1, readonly=True)
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position', 'Fiscal Position')
    vehicle_id = fields.Many2one('customer.vehicle', 'Vehicle')
    v_model_id = fields.Many2one(related='vehicle_id.model_id', string='Vehicle Model')
    v_brand_id = fields.Many2one(related='vehicle_id.brand_id', string='Vehicle Brand')
    v_l_num = fields.Char(related='vehicle_id.license_number', string='Vehicle Number')
    v_year = fields.Char(related='vehicle_id.year', string='Vehicle Year')
    v_fule_type_id = fields.Many2one(related='vehicle_id.fuel_type_id', string='Vehicle Fuel Type')
    # payments_ids = fields.One2many('account.bank.statement.line', 'repair_ord_pymt_id')
    mechanic_ids = fields.Many2many('hr.employee', string="Assign Mechanic", readonly=True)
    assign_bay_id = fields.Many2one('bay', 'Assign Bay', readonly=True)
    serice_history_ids = fields.One2many('service.history', 'repair_ord_history_id')
    removed_repair_ids = fields.One2many('remove.repair.line', 'repair_order_id')
    stock_picking_id = fields.Many2many("stock.picking", "stock_picking_default_rel", string="Stock Picking")
    rev_stock_picking_id = fields.Many2one("stock.picking", string="Reverse Stock Picking")
    remove_stock_picking_id = fields.Many2many("stock.picking", "remove_stock_picking_default_rel", string="Remove Stock Picking")
    other_loc_stock_picking_id = fields.Many2many("stock.picking", "other_loc_stock_picking_default_rel", string="Remove Stock Picking")
    pos_order_id = fields.Many2one("pos.order", string="Advance Payment", help="Advance Payment POS Order")
    final_pos_order_id = fields.Many2one("pos.order", string="POS Order")
    employee_id = fields.Many2one("hr.employee", "Cashier")
    planning_id = fields.Many2one("planning.slot", "Planning")
    back_order_ids = fields.Many2many("stock.picking", "back_order_stock_picking_default_rel", string="Back Order Stock Picking")
       
    def action_repair_cancel(self):
        res = super(RepairOrder, self).action_repair_cancel()
        pickings = self.stock_picking_id
        for picking in pickings:
            if picking.state in ['done']:
                rec = picking.create_reverse(self)
                if self.remove_stock_picking_id:
                    self.remove_stock_picking_id = [(4, rec.id)]
                else:
                    self.remove_stock_picking_id = [(6, 0, [rec.id])]
            if picking.state not in ['done', 'cancel']:
                picking.action_cancel()
        return res

    def _value_search(self, operator, value):
        recs = self.search([]).filtered(lambda x : x.picking_state == value)
        if recs:
            return [('id', 'in', [x.id for x in recs])]

    def _compute_picking_state(self):
        """
        Return the overall state of all stock.picking.
        """
        state_list = ['draft', 'waiting', 'confirmed', 'assigned']
        for rec in self:
            picking_state_list = [ii.state for ii in rec.stock_picking_id]
            if not picking_state_list:
                rec.picking_state = None
            else:
                states = [i for i in state_list if i in picking_state_list]
                if states:
                    rec.picking_state = 'waiting'
                else:
                    rec.picking_state = 'done'

    def dict_compare(self, d1, d2):
        d1_keys = set(d1.keys())
        d2_keys = set(d2.keys())
        intersect_keys = d1_keys.intersection(d2_keys)
        added = d1_keys - d2_keys
        removed = d2_keys - d1_keys
        modified = {o : (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
        same = set(o for o in intersect_keys if d1[o] == d2[o])
        return added, removed, modified, same

    @api.model
    def update_repair_order(self, data):
        """
        This function update repair.order which is loaded on POS.
        """
        newrelic.agent.set_transaction_name("update_repair_order_pos_repair_order", "/RepairOrder", priority=None)
        print(data['json'], data['order_vals'], '+++++++=')
        if 'repair_id' in data['json']:
            repair_obj = self.search([('id', '=', int(data['json']['repair_id']))])
        if 'repair_name' in data['json']:
            repair_obj = self.search([('name', '=', data['json']['repair_name'])])
        print(repair_obj, '++++repair_obj+++')


        order_vals = data['order_vals']
        print(order_vals, '+++++++order_vals++++++++++')
        if order_vals['repair_type']:
            repair_obj.repair_type = order_vals['repair_type']
        if order_vals['note']:
            repair_obj.internal_notes = order_vals['note']
        if order_vals['operation_type']:
            repair_obj.operation_type = order_vals['operation_type']
        if order_vals['odometer_reading']:
            repair_obj.odoometer_reading = order_vals['odometer_reading']
        if order_vals['delivery_date']:
            repair_obj.expected_delivery_date = datetime.strptime(order_vals['delivery_date'], "%Y/%m/%d %H:%M").strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)
        if order_vals['vehicle_id']:
            vehicle_obj = self.env['customer.vehicle'].search([('id', '=', int(order_vals['vehicle_id']))])
            repair_obj.vehicle_id = vehicle_obj.id
        if 'partner_id' in order_vals:
            print(order_vals['partner_id'], '+++++==partner_id+=====')
            if repair_obj.partner_id.id != order_vals['partner_id']:
                repair_obj.partner_id = order_vals['partner_id']

        # stock_before_update = {}
        # for line in repair_obj.operations:
        #     if not line.stock_loc_id:
        #         if line.product_id.id not in stock_before_update:
        #             stock_before_update[line.product_id.id] = line.product_uom_qty
        #         else:
        #             stock_before_update[line.product_id.id] += line.product_uom_qty
        # print(stock_before_update, '++++++++++++++++++++++++++')

        repair_obj.operations.unlink()
        repair_obj.fees_lines.unlink()               
        
        if 'lines' in data['json']:
            for line in data['json']['lines']:
                item = line[-1]
                if 'custom_discount_reason' in item:
                    del item['custom_discount_reason']
                if 'line_qty_returned' in item:
                    del item['line_qty_returned']
                if 'original_line_id' in item:            
                    del item['original_line_id']
                if 'pack_lot_ids' in item:            
                    del item['pack_lot_ids']
            print(data['json']['lines'], '++++++++lines++++++++')
            for line in data['json']['lines']:
                item = line[-1]
                product_obj = self.env['product.product'].search([('id', '=', int(item['product_id']))])
                print(product_obj, '++++product_obj')
                if product_obj != repair_obj.session_id.config_id.adv_pymt_product_id:
                    if product_obj.type not in ['service']:
                        self.env['repair.line'].create({
                            'repair_id': repair_obj.id,
                            'product_id': product_obj.id,
                            'product_uom_qty': item['qty'],
                            'type': 'add',
                            'location_id': repair_obj.warehouse_id.repair_operation_type.default_location_src_id.id,
                            'location_dest_id':repair_obj.warehouse_id.repair_operation_type.default_location_dest_id.id ,
                            'product_uom': product_obj.uom_id.id,
                            'discount': item['discount'],
                            'created_from': 'pos',
                            'price_unit': item['price_unit'],
                            'tax_id': item['tax_ids'],
                            **({'stock_loc_id': item['stock_location_id']} if 'stock_location_id' in item else {}),
                        })
                    else:
                        self.env['repair.fee'].create({
                            'repair_id': repair_obj.id,
                            'product_id': product_obj.id,
                            'name': product_obj.name,
                            'product_uom': product_obj.uom_id.id,
                            'product_uom_qty': item['qty'],
                            'price_unit': item['price_unit'],
                            'tax_id': item['tax_ids'],
                            'created_from': 'pos',
                        })

        repair_obj.confirm_repair_order()
        

        if repair_obj.repair_type == 'service':

            # stock_after_update = {}
            # for line in repair_obj.operations:
            #     if not line.stock_loc_id:
            #         if line.product_id.id not in stock_after_update:
            #             stock_after_update[line.product_id.id] = line.product_uom_qty
            #         else:
            #             stock_after_update[line.product_id.id] += line.product_uom_qty
            # print(stock_after_update, '++++++++++++++++++++++++++')

            # move_stock = {key: stock_before_update[key] - stock_after_update.get(key, 0) for key in stock_before_update.keys()} 
            # another_stock = { k : stock_after_update[k] for k in set(stock_after_update) - set(stock_before_update) }
            # total_stock = {**move_stock, **another_stock}

            print(repair_obj.stock_picking_id, '++++++stock_picking_id++++')
            print(repair_obj.remove_stock_picking_id, '+++++++remove_stock_picking_id++++++++++')
            add_stock = {}
            remove_stock = {}
            for picking in repair_obj.stock_picking_id:
                for move in picking.move_ids_without_package:
                    if move.product_id.id not in add_stock:
                        add_stock[move.product_id.id] = move.product_uom_qty
                    else:
                        add_stock[move.product_id.id] += move.product_uom_qty

            print(add_stock, '++++++add_stock')
            
            for picking in repair_obj.remove_stock_picking_id:
                for move in picking.move_ids_without_package:
                    if move.product_id.id not in remove_stock:
                        remove_stock[move.product_id.id] = move.product_uom_qty
                    else:
                        remove_stock[move.product_id.id] += move.product_uom_qty

            print(remove_stock, '++++++remove_stock')
            final_stock = {key: add_stock[key] - remove_stock .get(key, 0) for key in add_stock.keys()} 
            print(final_stock, '+++++++final_stock+++++')

            new_line_stock = {}
            for line in repair_obj.operations:
                if not line.stock_loc_id:
                    if line.product_id.id not in new_line_stock:
                        new_line_stock[line.product_id.id] = line.product_uom_qty
                    else:
                        new_line_stock[line.product_id.id] += line.product_uom_qty

            print(new_line_stock, '++new_line_stock+++++++')

            move_stock = {key: new_line_stock[key] - final_stock.get(key, 0) for key in new_line_stock.keys()} 
            another_stock = { k : (-1)*(final_stock[k]) for k in set(final_stock) - set(new_line_stock) }
            total_stock = {**move_stock, **another_stock}

            forward_stock_picking = None
            rev_stock_picking = None
            for key, value in total_stock.items(): 
                print(key,value) 

                if value > 0:
                    print(value, '++++++++++++11111111111111++++++++')
                    picking_type_id = repair_obj.warehouse_id.repair_operation_type
                    if not forward_stock_picking:
                        rec = self.env['stock.picking'].sudo().create({
                            **({'partner_id': repair_obj.partner_id.id} if repair_obj.partner_id.id else {}),
                            'picking_type_id': picking_type_id.id,
                            'location_id': picking_type_id.default_location_src_id.id,
                            'location_dest_id': picking_type_id.default_location_dest_id.id,
                            'origin': 'Stock Picking for '+ repair_obj.name,
                            'repair_obj_id': repair_obj.id
                        })
                        forward_stock_picking = rec
                        if repair_obj.stock_picking_id:
                            repair_obj.stock_picking_id = [(4, rec.id)]
                        else:
                            repair_obj.stock_picking_id = [(6, 0, [rec.id])]
                        product_obj = self.env['product.product'].search([('id', '=', int(key))])
                        self.env['stock.move'].sudo().create({
                            'picking_id': rec.id,
                            'product_id': int(key),
                            'product_uom_qty': int(value),
                            # 'quantity_done': int(value),
                            'product_uom': product_obj.uom_id.id,
                            'location_id': picking_type_id.default_location_src_id.id,
                            'location_dest_id': picking_type_id.default_location_dest_id.id,
                            'name': repair_obj.name
                        })
                    else:
                        product_obj = self.env['product.product'].search([('id', '=', int(key))])
                        self.env['stock.move'].sudo().create({
                            'picking_id': forward_stock_picking.id,
                            'product_id': int(key),
                            'product_uom_qty': int(value),
                            # 'quantity_done': int(value),
                            'product_uom': product_obj.uom_id.id,
                            'location_id': picking_type_id.default_location_src_id.id,
                            'location_dest_id': picking_type_id.default_location_dest_id.id,
                            'name': repair_obj.name
                        })
                elif value < 0:
                    print(value, '++++++++++++22222222222222++++++++', int(value) * (-1))
                    return_picking_type_id = repair_obj.warehouse_id.repair_operation_type.return_picking_type_id
                    if not rev_stock_picking:
                        rec = self.env['stock.picking'].sudo().create({
                            **({'partner_id': repair_obj.partner_id.id} if repair_obj.partner_id.id else {}),
                            'picking_type_id': return_picking_type_id.id,
                            'location_id': return_picking_type_id.default_location_src_id.id,
                            'location_dest_id': return_picking_type_id.default_location_dest_id.id,
                            'origin': 'Stock Picking for '+ repair_obj.name,
                            'repair_obj_id': repair_obj.id
                        })
                        rev_stock_picking = rec
                        if repair_obj.remove_stock_picking_id:
                            repair_obj.remove_stock_picking_id = [(4, rec.id)]
                        else:
                            repair_obj.remove_stock_picking_id = [(6, 0, [rec.id])]
                        product_obj = self.env['product.product'].search([('id', '=', int(key))])
                        self.env['stock.move'].sudo().create({
                            'picking_id': rec.id,
                            'product_id': int(key),
                            'product_uom_qty': int(value) * (-1),
                            # 'quantity_done': int(value) * (-1),
                            'product_uom': product_obj.uom_id.id,
                            'location_id': return_picking_type_id.default_location_src_id.id,
                            'location_dest_id': return_picking_type_id.default_location_dest_id.id,
                            'name': repair_obj.name
                        })
                    else:
                        product_obj = self.env['product.product'].search([('id', '=', int(key))])
                        self.env['stock.move'].sudo().create({
                            'picking_id': rev_stock_picking.id,
                            'product_id': int(key),
                            'product_uom_qty': int(value) * (-1),
                            # 'quantity_done': int(value) * (-1),
                            'product_uom': product_obj.uom_id.id,
                            'location_id': return_picking_type_id.default_location_src_id.id,
                            'location_dest_id': return_picking_type_id.default_location_dest_id.id,
                            'name': repair_obj.name
                        })
            
            print(forward_stock_picking, '++++++++forward_stock_picking++++')
            print(rev_stock_picking, '++++++++rev_stock_picking+++++++++')

            if forward_stock_picking:
                forward_stock_picking.action_confirm()
                forward_stock_picking.action_assign()
                for ii in forward_stock_picking.move_ids_without_package:
                    if ii.state not in ['assigned']:
                        forward_stock_picking.do_unreserve()
                        break
                if repair_obj.session_id.config_id.ro_stock_transfer:
                    forward_stock_picking.button_validate() 
                    for ii in forward_stock_picking.move_ids_without_package:
                        if ii.state not in ['assigned']:
                            forward_stock_picking.do_unreserve()
                            break
                
            if rev_stock_picking:
                rev_stock_picking.action_confirm()
                rev_stock_picking.action_assign()
                for ii in rev_stock_picking.move_ids_without_package:
                    if ii.state not in ['assigned']:
                        rev_stock_picking.do_unreserve()
                        break
                if repair_obj.session_id.config_id.ro_stock_transfer:
                    rev_stock_picking.button_validate()    
                    for ii in rev_stock_picking.move_ids_without_package:
                        if ii.state not in ['assigned']:
                            rev_stock_picking.do_unreserve()
                            break 

        return True

    def order_parts(self):
        """
        This function returns Tree/Form view action of all products from operations and fees_lines of repair.order.
        """
        product_ids = []
        for line in self.operations:
            product_ids.append(line.product_id.id)
        for line in self.fees_lines:
            product_ids.append(line.product_id.id)
        return {
            'name': ('Repair Order Products'),
            'view_mode': 'tree,form',
            'res_model': 'product.product',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', product_ids)]
        }

    def pos_order_related_to_ro(self):
        """
        This function returns Tree/Form view of all pos.order created for current repair.order.
        """
        pos_order_ids = []
        if self.pos_order_id:
            pos_order_ids.append(self.pos_order_id.id)
        if self.final_pos_order_id:
            pos_order_ids.append(self.final_pos_order_id.id)
        return {
            'name': ('POS Orders'),
            'view_mode': 'tree,form',
            'res_model': 'pos.order',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', pos_order_ids)]
        }
        
    
    def added_stock_picking(self):
        """
        This function return Tree/Form view action of stock.picking created while adding product to current repair.order.
        """
        stock_ids = [picking.id for picking in self.stock_picking_id]
        return {
            'name': ('Stock Picking of added items'),
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', stock_ids)]
        }

    def removed_stock_picking(self):
        """
        This function return Tree/Form view action of stock.picking created while removing product from current repair.order.
        """
        stock_ids = [picking.id for picking in self.remove_stock_picking_id]
        return {
            'name': ('Stock Picking of removed items'),
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', stock_ids)]
        }

    def other_locations_stock_picking(self):
        """
        This function return Tree/Form view action of stock.picking which is created from another stock location in POS.
        """
        stock_ids = [picking.id for picking in self.other_loc_stock_picking_id]
        return {
            'name': ('Stock Picking of other location items'),
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', stock_ids)]
        }

    def back_order_stock_picking(self):
        """
        This function return Tree/Form view action of stock.picking which is created in back order.
        """
        stock_ids = [picking.id for picking in self.back_order_ids]
        return {
            'name': ('Back Order of Stock Picking'),
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', stock_ids)]
        }

    def action_repair_end(self):
        """
        Overrode action_repair_end() method.
        """
        if self.filtered(lambda repair: repair.state != 'under_repair'):
            raise UserError(_("Repair must be under repair in order to end reparation."))
        for repair in self:
            repair.write({'repaired': True})
            vals = {'state': 'done'}
            if not repair.invoiced and repair.invoice_method == 'after_repair':
                vals['state'] = '2binvoiced'
            repair.write(vals)
        return True

    def action_validate(self):
        res = super(RepairOrder, self).action_validate()
        if self.repair_type == 'quote':
            self.repair_type = 'service'
            self.env['stock.picking'].sudo().create_picking_for_repair_order(self)
        if self.repair_type == 'service':
            self.env['stock.picking'].sudo().create_picking_for_repair_order(self)
        return res

    # @api.model
    def confirm_repair_order(self):
        """
        This function is called from js to call action_confirm of repair.order.
        """
        if self.repair_type == 'service' and self.state in ['draft']:
            res = self.action_validate()
            self.env['stock.picking'].sudo().create_picking_for_repair_order(self)

    def show_pickings(self):  
        """
        """
        self.ensure_one()
        pickings = []
        for item in self.stock_picking_id:
            pickings.append((0, 0,
                {
                    'picking_id' : item.id,
                    'state' : dict(self.env['stock.picking']._fields['state'].selection).get(item.state)
                }
            ))            
        ctx = dict(
            default_model = 'repair.order',
            default_repair_id = self.id,
            default_pickings_ids = pickings
        )
        return {
            'name': _('Stock Pickings'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'repair.order.pickings.wizard',
            'target': 'new',
            'context': ctx
        }

    def remove_item_repair_line(self):
        """ 
        """
        self.ensure_one()
        remove_item_line_data = []
        for item in self.operations:
            remove_item_line_data.append((0, 0,
                {
                    'product_id' : item.product_id.id,
                    'unit_price' : item.price_unit,
                    'product_uom_qty' : item.product_uom_qty,
                    'remove_qty': 0.0,
                    'remove_reason': '',
                    'line_id': item.id,
                    'line_obj': 'repair.line',
                }
            ))
        for item in self.fees_lines:
            remove_item_line_data.append((0, 0,
                {
                    'product_id' : item.product_id.id,
                    'unit_price' : item.price_unit,
                    'product_uom_qty' : item.product_uom_qty,
                    'remove_qty': 0.0,
                    'remove_reason': '',
                    'line_id': item.id,
                    'line_obj': 'repair.fee',
                }
            ))
        ctx = dict(
            default_model = 'repair.order',
            default_repair_id = self.id,
            default_removing_line_ids = remove_item_line_data
        )
        return {
            'name': _('Remove Item'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'remove.item.repair.line.wizard',
            'target': 'new',
            'context': ctx
        }

    @api.model
    def _get_default_product(self):
        pos_config_rec = self.env['pos.config'].sudo().search([], limit=1)
        if pos_config_rec and pos_config_rec.product_id:
            return pos_config_rec.product_id


    @api.depends('operations')
    def _compute_total(self):
        """
        This function compute total service time on parts and operations.
        """
        for rec in self:
            service_time = 0.0
            for line in rec.operations:
                service_time += (line.product_id.service_time)
            for line in rec.fees_lines:
                service_time += (line.product_id.service_time)
            rec.total_service_time = service_time
        
    
    def write(self, vals):
        """
        Overrider write() method to add record in service.history object on every state changes.
        """
        for obj in self:                
            if vals.get('state'):
                vals['serice_history_ids'] = [[0, 0, {
                    'label': 'State Change',
                    'user_id': self.env.user.id,
                    'action_time': datetime.now(),
                    'action_remark': '%s --> %s' % (dict(self._fields['state'].selection).get(obj.state), dict(self._fields['state'].selection).get(vals['state'])),
                    'repair_ord_history_id': obj.id
                }]]
            if vals.get('assign_bay_id'):
                bay_rec = self.env['bay'].sudo().search([('id', '=', vals['assign_bay_id'])])
                vals['serice_history_ids'] = [[0, 0, {
                    'label': 'Bay Assigned',
                    'user_id': self.env.user.id,
                    'action_time': datetime.now(),
                    'action_remark': '%s --> %s' % (bay_rec.bay_name, bay_rec.bay_code),
                    'repair_ord_history_id': obj.id
                }]]
            if vals.get('mechanic_ids'):
                mechanic_str = []
                for mechanic in vals['mechanic_ids'][0][-1]:
                    mechanic_rec = self.env['hr.employee'].search([('id', '=', mechanic)])
                    mechanic_str.append(mechanic_rec.name)
                vals['serice_history_ids'] = [[0, 0, {
                    'label': 'Mechanics Assigned',
                    'user_id': self.env.user.id,
                    'action_time': datetime.now(),
                    'action_remark': '%s' % (' , '.join(mechanic_str)),
                    'repair_ord_history_id': obj.id
                }]]
            if vals.get('quotation_id'):
                found_ids = self.env['repair.order'].search(
                    [('quotation_id', '=', vals['quotation_id'])]).ids
                if len(found_ids) > 0:
                    raise UserError(
                        "Please use some other Quotation Id !!!\nThis id has already been used for some other quotation.")
        return super(RepairOrder, self).write(vals)

    def click_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def send_by_email(self):
        partner_id = self.partner_id
        if not partner_id:
            raise UserError("Please select a Customer.")
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('pos_repair_order', 'email_template_pos_quotation')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        context=self._context
        if context == None:
            ctx = {}
        else:
            ctx = dict(context)
        self.write({'quotation_sent': True})
        ctx.update({
            'default_model': 'repair.order',
            'default_res_id': self.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            # 'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }


    @api.model
    def send_email_on_save(self,val):
        ir_model_data = self.env['ir.model.data']
        temp_id = self.env.ref('pos_repair_order.email_template_pos_quotation',False)
        if temp_id:
           temp_id.send_mail(val, force_send=True)
        return True

    @api.model
    def search_quotation(self,args):
        if args.get('quotation_id'):
            result = self.search([('quotation_id','=',args.get('quotation_id'))]).id
            if result:
                return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            print(vals, '==========vals')
            if vals.get('date_order') and type(vals.get('date_order')) == str:
                vals['date_order'] = datetime.strptime(vals['date_order'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)
            if not vals.get('date_order'):
                vals['date_order'] = datetime.now().strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)
            if vals.get('expected_delivery_date') and type(vals.get('expected_delivery_date')) == str:
                vals['expected_delivery_date'] = datetime.strptime(vals['expected_delivery_date'], "%Y/%m/%d %H:%M").strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)
            if not vals.get('user_id'):
                vals['user_id'] = self._uid
        res =  super(RepairOrder, self).create(vals_list)
        return res

    def check_available_in_pos(self, r_ids):
        """
        This function checks while loading any quotation all items are presend in POS or not. 
        """
        error_dict = {}
        error_list = []
        for r_obj in r_ids:
            for line in r_obj.operations:
                if not line.product_id.sale_ok or not line.product_id.available_in_pos:
                    error_list.append({
                        'product_id': line.product_id.id, 
                        'product_name':  line.product_id.name 
                    })
            for line in r_obj.fees_lines:
                if not line.product_id.sale_ok or not line.product_id.available_in_pos:
                    error_list.append({
                        'product_id': line.product_id.id, 
                        'product_name':  line.product_id.name 
                    })
        if len(error_list):
            error_dict['status'] = False
            error_dict['repair_name'] = r_ids[0].name
            error_dict['message'] = error_list
            error_dict['identifier'] = True
        else:
            error_dict['status'] = True
            error_dict['message'] = error_list
        return error_dict

    def get_data_of_lines(self, repair_obj, result):
        """
        Prepare orderline data from repair.line, repair.fees_lines and pos.order.line.
        """
        pos_config_id =  self.env['pos.config'].sudo().search([('warehouse_id', '=', repair_obj.warehouse_id.id)], limit=1)
        if repair_obj.pos_order_id:
            # pos_order_objs = self.env['pos.order'].search([('repair_id','=', repair_obj.id)], limit=1)        
            result['adv_pymt_done'] = True if repair_obj.pos_order_id else False
            result['pos_order_id'] = repair_obj.pos_order_id.id if repair_obj.pos_order_id else False
        print(dict(repair_obj._fields['state'].selection).get(repair_obj.state), '=================================')
        result['status'] = True
        result['repair_obj_id'] = repair_obj.id
        result['repair_state'] = dict(repair_obj._fields['state'].selection).get(repair_obj.state)
        result['repair_id'] = repair_obj.name
        result['repair_type'] = repair_obj.repair_type
        result['operation_type'] = repair_obj.operation_type
        result['note'] = repair_obj.internal_notes
        result['pricelist_id'] = repair_obj.pricelist_id.id
        result['amount_total'] = repair_obj.amount_total
        result['amount_tax'] = repair_obj.amount_tax
        if repair_obj.partner_id:
            result['partner_id'] = repair_obj.partner_id.id
        if repair_obj.vehicle_id:
            result['vehicle_id'] = repair_obj.vehicle_id.id
        if repair_obj.vehicle_id.brand_id.brand_name:
            result['brand'] = repair_obj.vehicle_id.brand_id.brand_name 
        if repair_obj.expected_delivery_date:
            result['delivery_date'] = repair_obj.expected_delivery_date     
        if repair_obj.vehicle_id.year:
            result['year'] = repair_obj.vehicle_id.year                 
        if repair_obj.vehicle_id.model_id.model_name:
            result['model'] = repair_obj.vehicle_id.model_id.model_name
        if repair_obj.vehicle_id.license_number:
            result['l_num'] = repair_obj.vehicle_id.license_number
        if repair_obj.vehicle_id.fuel_type_id.fuel_type:
            result['fuel_type'] = repair_obj.vehicle_id.fuel_type_id.fuel_type
        if repair_obj.repair_type:
            result['repair_type'] =  repair_obj.repair_type
        if repair_obj.odoometer_reading:
            result['odometer_reading'] = repair_obj.odoometer_reading
        result['line'] = []
        for line in repair_obj.operations:
            orderline = {}
            orderline['product_id'] = line.product_id.id
            orderline['price_unit'] = line.product_id.list_price if pos_config_id.load_with_special_price else line.price_unit
            orderline['qty'] = line.product_uom_qty
            orderline['discount'] = line.discount
            result['line'].append(orderline)
        for line in repair_obj.fees_lines:
            orderline = {}
            orderline['product_id'] = line.product_id.id
            orderline['price_unit'] = line.product_id.list_price if pos_config_id.load_with_special_price else line.price_unit
            orderline['qty'] = line.product_uom_qty
            result['line'].append(orderline)
        # if repair_obj.state in ['done']:
        #     result['adv_pymt_data'] = True
        for line in repair_obj.pos_order_id.lines:
            orderline = {}
            orderline['product_id'] = line.product_id.id
            orderline['price_unit'] = (-line.price_unit)
            orderline['qty'] = line.qty
            orderline['discount'] = line.discount
            result['line'].append(orderline)
        print(result, '++++result')
        return result
    
    @api.model
    def get_repair_details(self,kwargs):
        result = {}
        repair_objs = self.search([(
            'name', '=', kwargs['repair_id'])])
        r_search = self.search([('name', '=', kwargs['repair_id']), ('final_pos_order_id', '!=', False)])
        
        if len(repair_objs.ids) == 1 and not len(r_search):
            error_dict = self.check_available_in_pos(repair_objs)
            if not error_dict['status']:
                result = error_dict
                return result

        if len(repair_objs.ids) > 1:
            result['status'] = False
            result['message'] = 'Unknown Error!!! Contact your moderator.'
        elif repair_objs and len(r_search):
            result['message'] = 'Repair Order is completed.!!!'
        elif len(repair_objs.ids) == 0:
            if len(self.search([('name', '=', kwargs['repair_id']), ('state', '=', 'cancel')])):
                result['message'] = 'This quotation has been cancelled!!!'
            else:
                result['message'] = 'Quotation Id does not match any record!!!'
            result['status'] = False
        else:
            for repair_obj in repair_objs:
                result = self.get_data_of_lines(repair_obj, result)
        return result

    @api.model
    def cancel_repair_order(self, kwargs):
        """
        This method cancel the selected repair order from POS.
        """
        repair_obj = self.search([('name', '=', kwargs['repair_id'])], limit=1)
        if repair_obj:
            for picking in repair_obj.stock_picking_id:
                if picking.state != 'done':
                    picking.action_cancel()
            if repair_obj.state in ['draft', 'confirmed']:
                repair_obj.action_repair_cancel()
            return {'name': repair_obj.name}
        return {}

    
    # @api.model
    # def unlink_order(self, kwargs):
    #     """
    #     This method unlink repair order obj when POS delete order button is clicked.
    #     """
    #     result = {}
    #     repair_obj = self.search([('name', '=', kwargs['repair_name'])]) 
    #     if repair_obj: 
    #         repair_obj.unlink()
    #         result['status'] = True
    #         result['message'] = 'Repair order deleted successfully.!!!'
    #     else:
    #         result['status'] = False
    #         result['message'] = 'Repair Id does not match any record!!!'
    #     return result

    def cal_string(self, string):
        """
        This function returns list of string to POS OrderReceipt by splitting with '\n'.
        """
        output = string.split("\n")
        return output

    @api.model
    def reverse_move_for_ro(self, repair_id):
        """
        This function is used to check where repair order is in done state.
        """
        repair_id = repair_id['repair_id']
        repair_obj = self.search([('id', '=', repair_id)])
        # if repair_obj.state == 'done':
        repair_obj.stock_picking_id.create_rev_picking_for_repair_order(repair_obj)
        return {}
            # return {}
        # return {
        #     'obj_n':'repair.order',
        # }
    
    @api.model
    def auto_repair_order_transfer(self, data):
        """
        This function create stock.picking when auto transfer repair order 
        is checked in pos.config.
        """
        repair_id = data['repair_id']
        op_type_id = data['op_type_id']
        print(repair_id, op_type_id)
        repair_obj = self.search([('id', '=', repair_id)])
        op_type_obj = self.env['stock.picking.type'].search([('id', '=', int(op_type_id))])
        # if repair_obj.state == 'done' and op_type_obj:
        if op_type_obj:
            self.env['stock.picking'].auto_repair_order_transfer_picking(repair_obj, op_type_obj)
            return {}
        return {
            'obj_n':'repair.order',
        }

    @api.model
    def stock_picking_check(self, data):
        """
        This method check the state of stock picking and return
        status to POS.
        """
        repair_id = data['repair_id']
        repair_obj = self.search([('id', '=', repair_id)])
        pickings = repair_obj.stock_picking_id
        error_ll = []
        for picking in pickings:
            if picking.state not in ['cancel', 'done']:
                error_ll.append({
                    'picking_id': picking.id,
                    'picking_name': picking.name,
                    'picking_state': dict(self.env['stock.picking']._fields['state'].selection).get(picking.state)
                })
        if len(error_ll):
            return {
                'status': True,
                'data': error_ll,
                'repair_name': repair_obj.name
            }
        else:
            return {
                'status': False
            }

    @api.model
    def confirm_stock_picking_forcefully(self, data):
        """
        This method confirm all the stock picking
        forcefully from POS.
        """
        repair_id = data['repair_id']
        repair_obj = self.search([('id', '=', repair_id)])
        if repair_obj.state == 'draft':
            repair_obj.action_validate()
        if repair_obj.state == 'confirmed':
            repair_obj.action_repair_start()
        if repair_obj.state == 'under_repair':
            repair_obj.action_repair_end()
        pickings = repair_obj.stock_picking_id
        for picking in pickings:
            if picking.state in ['assigned']:
                rec = picking.button_validate()
                if 'res_id' in rec and 'res_model' in rec:
                    if rec['res_id'] and rec['res_model'] == 'stock.immediate.transfer':
                        wiz_rec = self.env['stock.immediate.transfer'].sudo().search([('id', '=', int(rec['res_id']))])
                        if wiz_rec:
                            wiz_rec.process()
            if picking.state not in ['cancel', 'done', 'assigned']:
                picking.extra_force_assign()
        return {
                'status': True
        }

    @api.model
    def get_quotation_name(self, quote):
        """
        This function is used to check where repair order is in done state.
        """
        repair_obj = self.search([('id', '=', int(quote))])
        return repair_obj.name


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # attributes
    quotation_print_type = fields.Selection([('pdf','Browser based (Pdf Report)'),('posbox','POSBOX (Xml Report)')], default='pdf', required=True)
    send_email_on_save_quotation = fields.Boolean(
        'Send Automatic Email on Save Quotation')
    ro_stock_transfer = fields.Boolean(string='Repair Order Stock Tranfer')
    po_stock_transfer = fields.Boolean(string='POS Order Stock Tranfer')
    store_policies = fields.Text(string="Store Policies")
    load_with_special_price = fields.Boolean(string="Load Repair order line with product special price.")
    auto_repair_order_transfer = fields.Boolean(string="Auto Repair Order Transfer")
    
    # relations
    product_id = fields.Many2one('product.product', string='Product to Repair', required=True, domain=[('available_in_pos', '=', True)])
    pr_uom_id = fields.Many2one('uom.uom', 'UOM', related='product_id.uom_id')
    # location_id = fields.Many2one('stock.location', 'Source Location', required=True)
    # location_dest_id = fields.Many2one('stock.location', 'Dest. Location', required=True)
    adv_pymt_product_id = fields.Many2one('product.product', 'Advance Payment Product', required=True, domain=[('available_in_pos', '=', True),('type', '=', 'service')])
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    repair_order_op_type = fields.Many2one('stock.picking.type', string='Repair Order Operation Type')

    def open_ui(self):
        for config in self:
            error = ''
            if not config.product_id:
                error += 'Product To Repair(Repair/Service Configuration) is Missing in Pos Config. \n'
            # if not config.location_id:
                # error += 'Product Location(Repair/Service Configuration) is Missing in Pos Config. \n'
            # if not config.location_dest_id:
                # error += 'Product Destionation Location(Repair/Service Configuration) is Missing in Pos Config. \n'
            if not config.adv_pymt_product_id:
                error += 'Advance Payment Product(Advance Payment Configuration) is Missing in Pos Config. \n'
            if not config.warehouse_id:
                error += 'Warehouse configurtion is Missing in Pos Config. \n'
            if error:
                raise ValidationError(error)
            else:
                return super(PosConfig, self).open_ui()

class RemovedRepairLine(models.Model):
    _name = "remove.repair.line"
    _description = "Removed Repair Lines"

    # attributes
    removed_qty = fields.Float("Removed Quantity")
    remove_reason = fields.Char("Remove Reason")
    timestamp = fields.Datetime("Timestamp")

    # relations
    product_id = fields.Many2one("product.product", string="Product")
    user_id = fields.Many2one("res.users", string="User")
    repair_order_id  = fields.Many2one("repair.order")
    rev_mov_id = fields.Many2one("stock.move", string="Reverse Move")