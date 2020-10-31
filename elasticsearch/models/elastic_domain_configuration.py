# -*- coding: utf-8 -*-

from odoo import api, fields, models,_
from odoo.exceptions import UserError


class ElasticDomainConfiguration(models.Model):
    _name = "elastic.domain.configuration"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Elastic Domain Configuration"
    _rec_name = "id"

    # attributes
    ec_field_operator = fields.Selection([
        ('=', '='),
        ('!=', '!='),
        ('like', 'like'),
        ('true', 'is True'),
        ('false', 'is False'),
    ], string='Operator', required=True)
    ec_field_value = fields.Char(string="Value")

    # relations
    ec_d_index_id = fields.Many2one("elastic.index.configuration", string="Index")
    ec_d_field_id = fields.Many2one("ir.model.fields", string="Field", required=True)
    ec_d_model_id = fields.Many2one("ir.model", related="ec_d_index_id.ec_model_id", string="Model", required=True)
