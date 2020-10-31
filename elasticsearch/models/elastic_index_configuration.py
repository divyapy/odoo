# -*- coding: utf-8 -*-

import logging
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient, IngestClient, ClusterClient, NodesClient, CatClient, SnapshotClient, TasksClient
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)
MODELDOMAIN = [("model", "in", ("product.template", "product.product", "product.attribute", "product.public.category", "product.brand.ept"))]


class ElasticIndexConfiguration(models.Model):
    _name = "elastic.index.configuration"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Elastic Index Configuration"
    _rec_name = "ec_name"

    # attributes
    state = fields.Selection([
        ('draft', 'Draft'),
        ('indexed', 'Indexed')
    ], string="State", default='draft')
    ec_name = fields.Char(string="Index Name")
    ec_domain = fields.Char(string="Domain", compute='_compute_filter')
    active = fields.Boolean(default=True, help="Set active to false to hide the Index without removing it.")

    # relations
    ec_model_id = fields.Many2one("ir.model", string="Model", domain=MODELDOMAIN, required=True)
    ec_fields_ids = fields.One2many("elastic.field.configuration", "ec_f_index_id", string="Fields")
    ec_domain_ids = fields.One2many("elastic.domain.configuration", "ec_d_index_id", string="Domains")

    @api.onchange('ec_model_id')
    def _onchange_ec_name(self):
        """
            method update the `ec_name` field value.
        """
        if self.ec_model_id:
            self.ec_name = self.ec_model_id.model.replace(".", "-")

    def _compute_filter(self):
        """
            this function create domain based on record
            added in `ec_domain_ids`.
        """
        domain = ""
        for obj in self.ec_domain_ids:
            if obj.ec_field_operator == 'true':
                domain += "('%s','=',True)," % obj.ec_d_field_id.name
            elif obj.ec_field_operator == 'false':
                domain += "('%s','=',False)," % obj.ec_d_field_id.name
        if self.ec_domain_ids:
            self.ec_domain = "[" + domain + "]"
        else:
            self.ec_domain = domain

    def prepare_field_mapping(self):
        """
            return dict of fields with there type for
            fields mapping with elastic server.
        """
        fields = {}
        fields.update({"id": {"type": "integer"}})
        if self.ec_model_id.model == 'product.template':
            fields.update({"autocomplete": {
                "type": "object",
                "dynamic": False
            }})
        for field in self.ec_fields_ids:
            fields.update(
            {field.ec_f_field_id.name: {
                "type": field.ec_field_type
            }})
        return fields

    def create_mappings(self):
        """
            this method will create index and
            field mapping at elastic server.
        """
        es_obj = self.env['elastic.server.configuration'].search([('active', '=', True)], limit=1)
        if not es_obj:
            raise UserError("No Active Elastic Server Configuration")
        try:
            if not self.exists_index(index=self.ec_name):
                field_mappings = self.prepare_field_mapping()
                mappings = {
                    "mappings": {
                        "properties": field_mappings,
                    }
                }
                try:
                    res = self.create_index(index=self.ec_name, body=mappings)
                    if 'acknowledged' in res and res['acknowledged']:
                        self.state = 'indexed'
                except Exception as e:
                    _logger.info("Exception on Create Mapping %s" % (e))
                    raise UserError("Exception on Create Mapping %s" % (e))
        except Exception as e:
            _logger.info("Exception on Create Mapping %s" % (e))
            raise UserError("Exception on Create Mapping %s" % (e))
        return True

    def update_mappings(self):
        """
            this method will update index and
            field mapping at elastic server.
        """
        es_obj = self.env['elastic.server.configuration'].search([('active', '=', True)], limit=1)
        if not es_obj:
            raise UserError("No Active Elastic Server Configuration")
        try:
            if self.exists_index(index=self.ec_name):
                field_mappings = self.prepare_field_mapping()
                mappings = {
                    "properties": field_mappings,
                }
                try:
                    res = self.put_mapping(index=self.ec_name,
                                        doc_type='_doc',
                                        body=mappings,
                                        include_type_name=True)
                    _logger.info("==update_mappings=====%s" % (res))
                    if 'acknowledged' in res and res['acknowledged']:
                        self.state = 'indexed'
                except Exception as e:
                    _logger.info("Exception on Update Mapping %s" % (e))
                    raise UserError("Exception on Update Mapping %s" % (e))
        except Exception as e:
            _logger.info("Exception on Update Mapping %s" % (e))
            raise UserError("Exception on Update Mapping %s" % (e))
        return True

    def prepare_searchable_fields(self):
        """
            return list of search field
            from index configuration.
        """
        fields = []
        for field in self.ec_fields_ids:
            if field.ec_searchable:
                fields.append(field.ec_f_field_id.name)
        return fields

    def product_attrs(self):
        """
            return the list of fields which need to sync
            at elastic server side.
        """
        product_attr = []
        for field in self.ec_fields_ids:
            product_attr.append(field.ec_f_field_id.name)
        return product_attr

    def create_mediator_rec(self):
        """
        create all records in `elastic.mediator` object.
        """
        mediator_obj = self.env["elastic.mediator"].sudo()
        if self.ec_domain:
            result = self.env[self.ec_model_id.model].search(safe_eval(self.ec_domain))
        else:
            result = self.env[self.ec_model_id.model].search([])
        for rec in result:
            mediator_obj.create({
                'ec_record_source': '%s,%s' % (self.ec_model_id.model, rec.id),
                'ec_index_id': self.id,
                'ec_record_id': rec.id,
                'ec_need_create': True,
            })

    ## Index Management

    @api.model
    def create_index(self, **kwargs):
        """
            http://elasticsearch-py.readthedocs.io/en/stable/api.html#elasticsearch.client.IndicesClient.create
            :param kwargs:
            :return:
        """
        es = self.env['elastic.server.configuration'].prepare_es_connection()
        res = IndicesClient(es).create(**kwargs)
        return res

    @api.model
    def delete_index(self, **kwargs):
        """
            http://elasticsearch-py.readthedocs.io/en/stable/api.html#elasticsearch.client.IndicesClient.delete
            :param kwargs:
            :return:
        """
        es = self.env['elastic.server.configuration'].prepare_es_connection()
        res = IndicesClient(es).delete(**kwargs)
        return res

    @api.model
    def get_index(self, **kwargs):
        """
            http://elasticsearch-py.readthedocs.io/en/stable/api.html#elasticsearch.client.IndicesClient.get
            :param kwargs:
            :return:
        """
        es = self.env['elastic.server.configuration'].prepare_es_connection()
        res = IndicesClient(es).get(**kwargs)
        return res

    @api.model
    def exists_index(self, **kwargs):
        """
            http://elasticsearch-py.readthedocs.io/en/stable/api.html#elasticsearch.client.IndicesClient.exists
            :param kwargs:
            :return:
        """
        es = self.env['elastic.server.configuration'].prepare_es_connection()
        res = IndicesClient(es).exists(**kwargs)
        return res

    ## Document Management

    @api.model
    def create_document(self, **kwargs):
        """
            https://elasticsearch-py.readthedocs.io/en/stable/api.html#elasticsearch.Elasticsearch.create
            :param kwargs:
            :return:
        """
        es = self.env['elastic.server.configuration'].prepare_es_connection()
        res = es.create(**kwargs)
        return res

    @api.model
    def bulk_document(self, **kwargs):
        """
            https://elasticsearch-py.readthedocs.io/en/master/api.html#elasticsearch.Elasticsearch.bulk
            :param kwargs:
            :return:
        """
        es = self.env['elastic.server.configuration'].prepare_es_connection()
        res = es.bulk(**kwargs)
        return res

    @api.model
    def delete_document(self, **kwargs):
        """
            https://elasticsearch-py.readthedocs.io/en/stable/api.html#elasticsearch.Elasticsearch.delete
            :param kwargs:
            :return:
        """
        es = self.env['elastic.server.configuration'].prepare_es_connection()
        res = es.delete(**kwargs)
        return res

    @api.model
    def exists_document(self, **kwargs):
        """
            https://elasticsearch-py.readthedocs.io/en/stable/api.html#elasticsearch.Elasticsearch.exists
            :param kwargs:
            :return:
        """
        es = self.env['elastic.server.configuration'].prepare_es_connection()
        res = es.exists(**kwargs)
        return res

    @api.model
    def exists_source_document(self, **kwargs):
        """
            https://elasticsearch-py.readthedocs.io/en/stable/api.html#elasticsearch.Elasticsearch.exists_source
            :param kwargs:
            :return:
        """
        es = self.env['elastic.server.configuration'].prepare_es_connection()
        res = es.exists_source(**kwargs)
        return res

    @api.model
    def get_document(self, **kwargs):
        """
            https://elasticsearch-py.readthedocs.io/en/stable/api.html#elasticsearch.Elasticsearch.get
            :param kwargs:
            :return:
        """
        es = self.env['elastic.server.configuration'].prepare_es_connection()
        res = es.get(**kwargs)
        return res

    @api.model
    def search_document(self, **kwargs):
        """
            https://elasticsearch-py.readthedocs.io/en/stable/api.html#elasticsearch.Elasticsearch.search
            :param kwargs:
            :return:
        """
        es = self.env['elastic.server.configuration'].prepare_es_connection()
        res = es.search(**kwargs)
        return res

    @api.model
    def update_document(self, **kwargs):
        """
            https://elasticsearch-py.readthedocs.io/en/stable/api.html#elasticsearch.Elasticsearch.update
            :param kwargs:
            :return:
        """
        es = self.env['elastic.server.configuration'].prepare_es_connection()
        res = es.update(**kwargs)
        return res

    @api.model
    def put_mapping(self, **kwargs):
        """
        http://elasticsearch-py.readthedocs.io/en/stable/api.html#elasticsearch.client.IndicesClient.put_mapping
        :param kwargs:
        :return:
        """
        es = self.env['elastic.server.configuration'].prepare_es_connection()
        res = IndicesClient(es).put_mapping(**kwargs)
        return res

    ## Website Methods

    def website_product_search(self, search, es_obj):
        """
            return the product after query from elastic server.
        """
        products = []
        if search:
            product_fields = es_obj.sudo().prepare_searchable_fields()
            es = self.env['elastic.server.configuration'].sudo().prepare_es_connection()
            product_body = {
                "size": 1000,
                "query": {
                    "multi_match": {
                        "query": search,
                        "fields": product_fields,
                        "fuzziness": "AUTO"
                    },
                }
            }
            product_res = es.search(index=es_obj.ec_name, doc_type="_doc", body=product_body)
            if 'hits' in product_res and product_res['hits']:
                product_res = product_res['hits']
                if 'hits' in product_res and product_res['hits']:
                    product_res = product_res['hits']
            for item in product_res:
                if "_id" in item:
                    products.append(item['_id'])

        ## Brand and Categories

        brands = []
        category = []

        brand_es_obj = self.sudo().search([('ec_name', '=', 'product-brand-ept')])
        brand_fields = brand_es_obj.sudo().prepare_searchable_fields()
        brand_body = {
            "query": {
                "multi_match": {
                    "query": search,
                    "fields": brand_fields,
                    "fuzziness": "AUTO"
                },
            }
        }

        category_es_obj = self.sudo().search([('ec_name', '=', 'product-public-category')])
        category_fields = category_es_obj.sudo().prepare_searchable_fields()
        category_body = {
            "query": {
                "multi_match": {
                    "query": search,
                    "fields": category_fields,
                    "fuzziness": "AUTO"
                },
            }
        }

        if brand_es_obj:
            brand_res = es.search(index=brand_es_obj.ec_name, doc_type="_doc", body=brand_body)
            if brand_res['hits']['total']['value'] > 0:
                for item in brand_res['hits']['hits']:
                    if '_source' in item:
                        brands.append(item['_source']['id'])

        if category_es_obj:
            category_res = es.search(index=category_es_obj.ec_name, doc_type="_doc", body=category_body)
            if category_res['hits']['total']['value'] > 0:
                for item in category_res['hits']['hits']:
                    if '_source' in item:
                        category.append(item['_source']['id'])

        ## Brand and Categories

        return {
                'products': products,
                'brands': brands,
                'category': category,
            }

    def website_autocomplete_product_search(self, search, es_obj, limit):
        """
            return the product after query from elastic server
            for autocomplete feature.
        """
        products = []
        brands = []
        category = []
        variant = []
        if search:
            product_fields = es_obj.sudo().prepare_searchable_fields()
            es = self.env['elastic.server.configuration'].sudo().prepare_es_connection()
            product_body = {
                "query": {
                    "multi_match": {
                        "query": search,
                        "fields": product_fields,
                        "fuzziness": "AUTO"
                    },
                }
            }

            brand_es_obj = self.sudo().search([('ec_name', '=', 'product-brand-ept')])
            brand_fields = brand_es_obj.sudo().prepare_searchable_fields()
            brand_body = {
                "query": {
                    "multi_match": {
                        "query": search,
                        "fields": brand_fields,
                        "fuzziness": "AUTO"
                    },
                }
            }

            category_es_obj = self.sudo().search([('ec_name', '=', 'product-public-category')])
            category_fields = category_es_obj.sudo().prepare_searchable_fields()
            category_body = {
                "query": {
                    "multi_match": {
                        "query": search,
                        "fields": category_fields,
                        "fuzziness": "AUTO"
                    },
                }
            }

            variant_es_obj = self.sudo().search([('ec_name', '=', 'product-product')])
            variant_fields = variant_es_obj.sudo().prepare_searchable_fields()
            variant_body = {
                "query": {
                    "match": {
                        variant_fields[0]: {
                            "query": search
                        }
                    }
                }
            }

            product_res = es.search(index=es_obj.ec_name, doc_type="_doc", body=product_body)
            if brand_es_obj:
                brand_res = es.search(index=brand_es_obj.ec_name, doc_type="_doc", body=brand_body)
                if brand_res['hits']['total']['value'] > 0:
                    for item in brand_res['hits']['hits']:
                        if '_source' in item:
                            brands.append(item['_source']['id'])

            if category_es_obj:
                category_res = es.search(index=category_es_obj.ec_name, doc_type="_doc", body=category_body)
                if category_res['hits']['total']['value'] > 0:
                    for item in category_res['hits']['hits']:
                        if '_source' in item:
                            category.append(item['_source']['id'])

            if variant_es_obj:
                variant_res = es.search(index=variant_es_obj.ec_name, doc_type="_doc", body=variant_body)
                if variant_res['hits']['total']['value'] > 0:
                    for item in variant_res['hits']['hits']:
                        if '_source' in item:
                            variant.append({
                                item['_source']['id']: item['_source']['product_tmpl_id']
                            })

            if 'hits' in product_res and product_res['hits']:
                product_res = product_res['hits']
                if 'hits' in product_res and product_res['hits']:
                    product_res = product_res['hits']
            for item in product_res:
                if '_source' in item:
                    products.append(item['_source']['autocomplete'])

        priority_res = self.env['elastic.priority'].sudo().search([], order='sequence')
        priority_data = [item.ec_model_id.model for item in priority_res]
        priority_sorted_data = []
        for item in priority_data:
            if item == 'product.template':
                priority_sorted_data.append("products")
            if item == 'product.brand.ept':
                priority_sorted_data.append("brands")
            if item == 'product.public.category':
                priority_sorted_data.append("categorys")
        return {
            'products': products[:limit],
            'products_count': len(products),
            'brands': brands,
            'category': category,
            'variant': variant,
            'sequence': priority_sorted_data
        }

    # def website_attribute_search(self, es_obj, ec_products):
    #     """
    #         return the attributes after query from elastic server.
    #     """
    #     attributes = []
    #     es = self.env['elastic.server.configuration'].sudo().prepare_es_connection()
    #     body = {
    #         "query" : {
    #             "terms" : {
    #                 "product_tmpl_ids": ec_products,
    #                 "boost": 1.0
    #             }
    #         }
    #     }
    #     res = es.search(index=es_obj.ec_name, doc_type="_doc", body=body)
    #     if 'hits' in res and res['hits']:
    #         res = res['hits']
    #         if 'hits' in res and res['hits']:
    #             res = res['hits']
    #     for item in res:
    #         if "_id" in item:
    #             attributes.append(item['_id'])
    #     return attributes

    # def website_categories_search(self, es_obj, search_product):
    #     """
    #         return the categories after query from elastic server.
    #     """
    #     categories = []
    #     es = self.env['elastic.server.configuration'].sudo().prepare_es_connection()
    #     body = {
    #         "query" : {
    #             "terms" : {
    #                 "product_tmpl_ids": search_product,
    #                 "boost": 1.0
    #             }
    #         }
    #     }
    #     res = es.search(index=es_obj.ec_name, doc_type="_doc", body=body)
    #     if 'hits' in res and res['hits']:
    #         res = res['hits']
    #         if 'hits' in res and res['hits']:
    #             res = res['hits']
    #     for item in res:
    #         if "_id" in item:
    #             categories.append(item['_id'])
    #     return categories
