# -*- coding: utf-8 -*-

import base64

from odoo import fields, models, tools
from odoo.modules.module import get_module_resource


CATEGORY_SELECTION = [
    ('required', 'Required'),
    ('optional', 'Optional'),
    ('no', 'None')]


class ProcurementApprovalCategory(models.Model):
    _name = 'procurement.approval.category'
    _description = 'Procurement Approval Category'
    _order = 'sequence'

    def _get_default_image(self):
        default_image_path = get_module_resource('mg_approval', 'static/src/img', 'clipboard-check-solid.svg')
        return base64.b64encode(open(default_image_path, 'rb').read())

    name = fields.Char(string="Name", translate=True, required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(string="Sequence")
    description = fields.Char(string="Description", translate=True)
    image = fields.Binary(string='Image', default=_get_default_image)
    approval_minimum = fields.Integer(string="Minimum Approval", default="1", required=True)
    is_manager_approver = fields.Boolean(
        string="Employee's Manager",
        help="Automatically add the manager as approver on the request.")
    user_ids = fields.Many2many('res.users', string="Approvers")
    request_to_validate_count = fields.Integer("Number of requests to validate", compute="_compute_request_to_validate_count")
    category_type = fields.Selection([('ss', 'Single Source'),('pr', 'Purchase Request')], string="Category Type")

    def _compute_request_to_validate_count(self):
        domain = [('request_status', '=', 'pending'), ('approver_ids.user_id', '=', self.env.user.id)]
        requests_data = self.env['approval.request'].read_group(domain, ['category_id'], ['category_id'])
        requests_mapped_data = dict((data['category_id'][0], data['category_id_count']) for data in requests_data)
        for category in self:
            category.request_to_validate_count = requests_mapped_data.get(category.id, 0)

    def create_request(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "material.purchase.requisition",
            "views": [[False, "form"]],
            "context": {
                'form_view_initial_mode': 'edit',
                'default_name': self.name,
                'default_category_id': self.id,
                'default_request_owner_id': self.env.user.id,
                'default_request_status': 'new'
            },
        }
