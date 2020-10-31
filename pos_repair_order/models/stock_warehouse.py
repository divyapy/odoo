# -*- coding: utf-8 -*-

from odoo import api, fields, models

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    # attributes
    transfer_stock_on_rrot = fields.Boolean('Validate on RROT')

    # relations
    repair_operation_type = fields.Many2one("stock.picking.type", string="Repair Operation Type", required=True)
    transit_locations_id = fields.Many2one("stock.location", string="Transit Location")