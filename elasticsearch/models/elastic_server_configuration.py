# -*- coding: utf-8 -*-

import logging
from elasticsearch import Elasticsearch

from odoo import api, fields, models,_
from odoo.exceptions import UserError
from odoo.tools import ustr

_logger = logging.getLogger(__name__)


class ElasticServerConfiguration(models.Model):
    _name = "elastic.server.configuration"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Elastic Server Configuration"
    _rec_name = "id"

    # attributes
    ec_name = fields.Char(string="Name", required=True)
    ec_limit = fields.Integer(string="Sync Limit", default=100)
    ec_host = fields.Char(string="Host", required=True)
    ec_is_port = fields.Boolean(string="Is Port ?")
    ec_port = fields.Integer(string="Port")
    ec_url_prefix = fields.Selection([
        ('http', 'Http'),
        ('https', 'Https'),
    ], string="URL Prefix", required=True)
    ec_timeout = fields.Integer(string="Timeout", default=10)
    ec_auth_type = fields.Selection([
        ('http_auth', 'Http Auth'),
        ('other', 'Other')
    ], string="Auth Type", required=True)
    ec_username = fields.Char(string="Username")
    ec_password = fields.Char(string="Password")
    ec_other_auth_details = fields.Char(string="Other Auth Detail")
    active = fields.Boolean(default=False, help="Set active to false to hide the Index without removing it.")

    def _geturl(self):
        """
            return the url of elastic server by using above configuration.
        """
        obj = self.search([('active', '=', True)], limit=1)
        url = "%s://%s%s" % (obj.ec_url_prefix, obj.ec_host, ':' + str(obj.ec_port) if obj.ec_is_port else '')
        return url, obj

    def test_ec_connection(self):
        """
            method checks the connection with elastic server.
        """
        es = self.prepare_es_connection()
        if es and es.ping():
            title = _("Connection Test Succeeded!")
            message = _("Everything seems properly set up!")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': message,
                    'sticky': False,
                }
            }
        if not es or not es.ping():
            raise UserError(_("Connection Test Failed! Please check your server Credentials!"))

    def prepare_es_connection(self):
        """
            method prepare connection with elastic server.
        """
        url, obj = self._geturl()
        if url and obj:
            es = Elasticsearch([url], http_auth=(obj.ec_username, obj.ec_password), timeout=obj.ec_timeout)
            return es

    def make_active(self):
        """
            this method will make record inactive.
        """
        for rec in self:
            rec.active = True

    def make_inactive(self):
        """
            this method will make record active.
        """
        for rec in self:
            rec.active = False
