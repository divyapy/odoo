# -*- coding: utf-8 -*-

from odoo import api, fields, models,_
from odoo.exceptions import UserError


class ElasticFieldConfiguration(models.Model):
    _name = "elastic.field.configuration"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Elastic Field Configuration"
    _rec_name = "id"

    # attributes
    ec_field_type = fields.Selection([
        ('keyword', 'Keyword'),
        ('text', 'Text'),
        ('double', 'Double'),
        ('float', 'Float'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('date', 'Date'),
        ('ip', 'IP'),
        ('array', 'Array'),
        ('object', 'Object')
    ], string='Field Type', default='text', required=True)
    ec_searchable = fields.Boolean(string="Is Searchable ?")

    # relations
    ec_f_index_id = fields.Many2one("elastic.index.configuration", string="Index")
    ec_f_field_id = fields.Many2one("ir.model.fields", string="Field")
    ec_f_model_id = fields.Many2one("ir.model", related="ec_f_index_id.ec_model_id", string="Model", required=True)
