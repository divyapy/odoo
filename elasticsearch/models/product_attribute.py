# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    def create_em_record(self, ei_obj, rec):
        """
            method will create `elastic.mediator` objects record.
        """
        MediatorObj = self.env["elastic.mediator"].sudo()
        obj = MediatorObj.create({
            'ec_record_id': rec.id,
            'ec_need_create': True,
            'ec_index_id': ei_obj.id,
            'ec_record_source': '%s,%s' % (ei_obj.ec_model_id.model, rec.id)
        })

    def update_em_record(self, ei_obj, rec):
        """
            method will update `elastic.mediator` objects record.
        """
        MediatorObj = self.env["elastic.mediator"].sudo()
        obj = MediatorObj.search([
            ('ec_record_id', '=', rec.id),
            ('ec_index_id', '=', ei_obj.id)
        ])
        if obj:
            obj.ec_need_update = True

    @api.depends('attribute_line_ids.active', 'attribute_line_ids.product_tmpl_id')
    def _compute_products(self):
        result = super(ProductAttribute, self)._compute_products()
        ei_obj =  self.env['elastic.index.configuration'].search([('ec_name', '=', self._name.replace(".", "-"))])
        if ei_obj:
            for obj in self:
                MediatorObj = self.env["elastic.mediator"].sudo()
                if not MediatorObj.search([('ec_record_id', '=', obj.id)]):
                    self.create_em_record(ei_obj, obj)
                else:
                    self.update_em_record(ei_obj, obj)
        return result
