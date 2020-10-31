# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models,_
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ElasticMediator(models.Model):
    _name = "elastic.mediator"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Elastic Mediator"
    _rec_name = "id"

    def _get_models(self):
        return [(rec.model, rec.name) for rec in self.env["ir.model"].search([])]

    # attributes
    ec_need_create = fields.Boolean(string="Need to Create")
    ec_need_update = fields.Boolean(string="Need to Update")
    ec_record_id = fields.Integer(string="Elastic Record", readonly=True)

    # relations
    ec_record_source = fields.Reference(selection=_get_models, string='Odoo Record',
        help="Source Model of the record in Mapping Table.", readonly=True)
    ec_index_id = fields.Many2one("elastic.index.configuration", string="Index", readonly=True)

    def product_attrs_for_ec_field(self, ei_obj):
        """
            return the list of fields which need to sync
            at elastic server side.
        """
        product_attr = []
        if ei_obj:
            for field in ei_obj.ec_fields_ids:
                product_attr.append(field.ec_f_field_id.name)
        return product_attr

    def update_rec_at_ec(self, obj):
        """
            this method updates record data at elastic server.
        """
        data = {}
        IndexObj = self.env['elastic.index.configuration'].sudo()
        product_attr = self.product_attrs_for_ec_field(obj.ec_index_id)
        record = obj.ec_record_source.read(product_attr)
        if obj.ec_record_source._name == 'product.template':
            combination_info = obj.ec_record_source._get_combination_info(only_template=True)
            fields = ['id', 'name', 'website_url', 'description_sale']
            json_rec = obj.ec_record_source.read(fields)
            data = {
                'autocomplete': {**combination_info, **json_rec[0]}
            }
        try:
            if IndexObj.exists_document(index=obj.ec_index_id.ec_name, doc_type='_doc', id=obj.ec_record_id):
                try:
                    res = IndexObj.update_document(index=obj.ec_index_id.ec_name, doc_type='_doc', id=obj.ec_record_id, body={'doc':{**record[0], **data}}, refresh=True)
                    _logger.info("%s RES, Record updated at EC."%(res))
                    if 'result' in res and res['result'] == 'updated':
                        obj.ec_need_update = False
                        self.env.cr.commit()
                except Exception as e:
                    _logger.info("Update Document %s Exception %s " % (obj.ec_record_id, e))
        except Exception as e:
            _logger.info("Exist Document %s Exception %s " % (obj.ec_record_id, e))

    def create_rec_at_ec(self, obj):
        """
            this method creates record data at elastic server.
        """
        data = {}
        IndexObj = self.env['elastic.index.configuration'].sudo()
        product_attr = self.product_attrs_for_ec_field(obj.ec_index_id)
        record = obj.ec_record_source.read(product_attr)
        if obj.ec_record_source._name == 'product.template':
            combination_info = obj.ec_record_source._get_combination_info(only_template=True)
            fields = ['id', 'name', 'website_url', 'description_sale']
            json_rec = obj.ec_record_source.read(fields)
            data = {
                'autocomplete': {**combination_info, **json_rec[0]}
            }
        try:
            if not IndexObj.exists_document(index=obj.ec_index_id.ec_name, doc_type='_doc', id=obj.ec_record_id):
                try:
                    res = IndexObj.create_document(index=obj.ec_index_id.ec_name, doc_type='_doc', id=obj.ec_record_id, body={**record[0], **data}, refresh=True)
                    _logger.info("%s RES, Record created at EC."%(res))
                    if 'result' in res and res['result'] == 'created':
                        obj.ec_need_create = False
                        self.env.cr.commit()
                except Exception as e:
                    _logger.info("Create Document %s Exception %s " % (obj.ec_record_id, e))
        except Exception as e:
            _logger.info("Exist Document %s Exception %s " % (obj.ec_record_id, e))

    def sync_rec_to_elastic(self):
        """
            this method will sync record from `elastic.mediator` to
            elastic server periodically.
        """
        es_obj = self.env['elastic.server.configuration'].search([('active', '=', True)], limit=1)
        if es_obj:
            objects = self.search(['|', ('ec_need_create', '=', True), ('ec_need_update', '=', True)], limit=es_obj.ec_limit)
            for obj in objects:
                if obj.ec_need_update:
                    self.update_rec_at_ec(obj)
                if obj.ec_need_create:
                    self.create_rec_at_ec(obj)
