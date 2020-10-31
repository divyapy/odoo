# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class PRRejectWizard(models.TransientModel):
    _name = 'pr.reject.wizard'
    _description = 'PR Reject'

    # attributes
    refused_attachment_id = fields.Binary(string="Attachment", attachment=True)
    att_id = fields.Many2one("ir.attachment")
    refused_comments = fields.Text(string="Comments")
    refused_rework = fields.Text(string="Rework")

    # relations
    requisition_id = fields.Many2one("material.purchase.requisition", string="Requisition")

    def reject(self):
        """
        This method reject PR.
        """
        obj = self.env['procurement.approval.approver'].search([
            ('user_id', '=', self.env.user.id),
            ('request_id', '=', self.requisition_id.id),
        ], limit=1)
        if self.refused_attachment_id:
            attachment = self.env['ir.attachment'].create({
                'name': 'name',
                'datas': self.refused_attachment_id,
                'res_model': 'procurement.approval.approver',
                'res_id': obj.request_id,
                'type': 'binary',
                'public': True
            })
            obj.refused_attachment_id = attachment.id
        obj.refused_comments = self.refused_comments
        obj.refused_rework = self.refused_rework
        obj.request_id.action_pr_refuse()
        return True
