# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class PRApproveWizard(models.TransientModel):
    _name = 'pr.approve.wizard'
    _description = 'PR Approve'

    # attributes
    approve_attachment_id = fields.Binary(string="Attachment", attachment=True)
    approve_comments = fields.Text(string="Comments")
    approve_rework = fields.Text(string="Rework")

    # relations
    requisition_id = fields.Many2one("material.purchase.requisition", string="Requisition")

    def approve(self):
        """
        This method approves PR.
        """
        obj = self.env['procurement.approval.approver'].search([
            ('user_id', '=', self.env.user.id),
            ('request_id', '=', self.requisition_id.id),
        ], limit=1)
        if self.approve_attachment_id:
            attachment = self.env['ir.attachment'].create({
                'name': 'name',
                'datas': self.approve_attachment_id,
                'res_model': 'procurement.approval.approver',
                'res_id': obj.request_id,
                'type': 'binary',
                'public': True
            })
            obj.approve_attachment_id = attachment.id
        obj.approve_comments = self.approve_comments
        obj.approve_rework = self.approve_rework
        obj.request_id.action_pr_approve()
        return True
