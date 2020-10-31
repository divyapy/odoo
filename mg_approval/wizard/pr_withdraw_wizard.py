# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class PRApproveWizard(models.TransientModel):
    _name = 'pr.withdraw.wizard'
    _description = 'PR Withdram'

    # attributes
    cancel_attachment_id = fields.Binary(string="Attachment", attachment=True)
    att_id = fields.Many2one("ir.attachment")
    cancel_comments = fields.Text(string="Comments")
    cancel_rework = fields.Text(string="Rework")

    # relations
    requisition_id = fields.Many2one("material.purchase.requisition", string="Requisition")

    def withdraw(self):
        """
        This method withdraw PR.
        """
        obj = self.env['procurement.approval.approver'].search([
            ('user_id', '=', self.env.user.id),
            ('request_id', '=', self.requisition_id.id),
        ], limit=1)
        if self.cancel_attachment_id:
            attachment = self.env['ir.attachment'].create({
                'name': 'name',
                'datas': self.cancel_attachment_id,
                'res_model': 'procurement.approval.approver',
                'res_id': obj.request_id,
                'type': 'binary',
                'public': True
            })
            obj.cancel_attachment_id = attachment.id
        obj.cancel_comments = self.cancel_comments
        obj.cancel_rework = self.cancel_rework
        obj.request_id.action_pr_withdraw()
        return True
