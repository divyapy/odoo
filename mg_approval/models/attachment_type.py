# -*- coding: utf-8 -*-

from odoo import models, fields


class AttachmentType(models.Model):
    _name = "attachment.type"
    _inherit = "mail.thread"
    _description = "Attachment Type Configuration"
    _rec_name = "name"

    name = fields.Char(string='Name', required=True)
    attachment_type = fields.Selection([
        ('pr', 'PR'),
        ('sourcing', 'Sourcing'),
        ('rfq', 'RFQ')
    ], string='Type')
    is_mandatory = fields.Boolean('Mandatory') 
    active = fields.Boolean('Active', default=True) 
    