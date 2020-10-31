# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models,_
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
MODELDOMAIN = [("model", "in", ("product.template", "product.public.category", "product.brand.ept"))]


class ElasticPriority(models.Model):
    _name = 'elastic.priority'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Elastic Priority"
    _rec_name = "id"
    _order = "sequence,id"

    # attributes
    sequence = fields.Integer("Sequence", default=10)
    active = fields.Boolean(default=True, help="Set active to false to hide the Index without removing it.")

    # relations
    ec_model_id = fields.Many2one("ir.model", string="Model", domain=MODELDOMAIN, required=True)

    _sql_constraints = [
        ('ec_model_id_uniq', 'unique (ec_model_id)', 'The Model must be unique per record !'),
    ]
