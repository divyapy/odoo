# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = "res.partner"

    # attributes
    is_mechanic = fields.Boolean(string="Is Mechanic")