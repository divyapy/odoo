# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError


class MaterialPurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'

    state = fields.Selection(selection_add=[('sourcing_created', 'Sourcing Document Created')])
    pr_id = fields.Many2one('purchase.requisition', string="Purchase Requisition", copy=False, readonly=True)

    def open_pr(self,):
        return {
            'name': _('%s' % self.pr_id.name),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('mg_purchase.purchase_req_inherit_form_view').id,
            'res_model': 'purchase.requisition',
            'res_id': self.pr_id.id
        }

    def launch_sourcing_creation_wizard(self, ):
        self.ensure_one()
        ctx = dict()
        return {
            'name': _('Create Sourcing Document'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'wiz.create.tender',
            'target': 'new',
            'context': ctx
        }
