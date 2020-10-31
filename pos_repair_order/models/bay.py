# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Bay(models.Model):
    _name = 'bay'
    _description = 'Bay'
    _rec_name = 'bay_code'

    # attributes
    bay_name = fields.Char("Name")
    bay_code = fields.Char("Code")
    color = fields.Integer("Color", default=0)

    # relations
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

    def name_get(self):
        res = []
        for bay in self:
            name = '[%s] %s' % (bay.bay_code, bay.bay_name)
            res.append((bay.id, name))
        return res