# -*- coding: utf-8 -*-

from odoo import models, fields


class AttachmentStatus(models.Model):
    _name = "attachment.status"
    _inherit = "mail.thread"
    _description = "Attachment Status Configuration"
    _rec_name = "name"

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean('Active', default=True) 