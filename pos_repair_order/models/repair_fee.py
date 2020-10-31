# -*- coding: utf-8 -*-

from odoo import api, fields, models

class RepairFee(models.Model):
    _inherit = 'repair.fee'

    created_from = fields.Selection([('pos', 'POS'),('manual', 'Manual')], 'Created From', default='manual')