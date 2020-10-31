# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models,_
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class ProductBrandEpt(models.Model):
    _inherit = 'product.brand.ept'

    def product_attrs_for_ec(self):
        """
            return the list of fields which need to sync
            at elastic server side.
        """
        ei_obj =  self.env['elastic.index.configuration'].search([('ec_name', '=', self._name.replace(".", "-"))])
        product_attr = []
        if ei_obj:
            for field in ei_obj.ec_fields_ids:
                product_attr.append(field.ec_f_field_id.name)
        return product_attr

    def create_em_record(self, ei_obj, rec):
        """
            method will create `elastic.mediator` objects record.
        """
        MediatorObj = self.env["elastic.mediator"].sudo()
        MediatorObj.create({
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

    def write(self, vals):
        print('+++++++ProductBrandEpt++++++++++++create')
        print(self, vals, '==========self, vals============')
        result = super(ProductBrandEpt, self).write(vals)
        product_attr = self.product_attrs_for_ec()
        intersection = list(set(vals.keys()).intersection(product_attr))
        ei_obj =  self.env['elastic.index.configuration'].search([('ec_name', '=', self._name.replace(".", "-"))])
        print(ei_obj, '=================ei_obj======write')
        if intersection and ei_obj:
            MediatorObj = self.env["elastic.mediator"].sudo()
            for rec in self:
                print(rec, '==============rec=========')
                domain_check = rec.filtered_domain(safe_eval(ei_obj.ec_domain)) if ei_obj.ec_domain else rec
                print(domain_check, '===========domain_check')
                if len(domain_check):
                    if not MediatorObj.search([('ec_record_id', '=', rec.id)]):
                        self.create_em_record(ei_obj, rec)
                    else:
                        self.update_em_record(ei_obj, rec)
        return result

    @api.model
    def create(self, vals):
        print('+++++++ProductBrandEpt++++++++++++create')
        result = super(ProductBrandEpt, self).create(vals)
        product_attr = self.product_attrs_for_ec()
        intersection = list(set(vals.keys()).intersection(product_attr))
        ei_obj =  self.env['elastic.index.configuration'].search([('ec_name', '=', self._name.replace(".", "-"))])
        print(ei_obj, '=================ei_obj======create')
        if intersection and ei_obj:
            for rec in result:
                print(ei_obj.ec_domain, '============ei_obj.ec_domain')
                domain_check = rec.filtered_domain(safe_eval(ei_obj.ec_domain)) if ei_obj.ec_domain else rec
                if len(domain_check):
                    self.create_em_record(ei_obj, rec)
        return result

