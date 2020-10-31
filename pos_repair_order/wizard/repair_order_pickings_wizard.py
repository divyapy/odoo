# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class RepairOrderPickings(models.TransientModel):
    _name = 'repair.order.pickings.wizard'
    _description = 'Repair Order Pickings'

    # relations
    repair_id = fields.Many2one("repair.order", string="Repair")
    pickings_ids = fields.One2many("repair.order.picking.items.wizard", "repair_order_pickings_id", string = "Picking Items")

class RepairOrderPickingItem(models.TransientModel):
    _name = 'repair.order.picking.items.wizard'
    _description = 'Repair Order Picking Items'

    # attributes
    state = fields.Char('State')

    # relations
    picking_id = fields.Many2one("stock.picking", string="Picking")
    repair_order_pickings_id = fields.Many2one("repair.order.pickings.wizard")