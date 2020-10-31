# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class PurchaseActionDashboardWizard(models.TransientModel):
    _name = 'purchase.action.dashboard.wizard'
    _description = 'Purchase Action Dashboard Wizard'

    # attributes
    pr_accept_date = fields.Date(string="PR Accept Date")
    tr_approved_on = fields.Date(string="TR Approved ON")
    bid_list_approved_date = fields.Date(string="Bid List Approve Date")
    target_price_sent_on = fields.Date(string="Target Price Send ON")
    rfq_sent_on = fields.Date(string="RFQ Sent ON")
    final_quote_receipt = fields.Char(string="Final Quote Receipt")
    first_quote_receipt_on = fields.Date(string="First Quote Receipt ON")
    sourcing_completed_on = fields.Date(string="Sourcing Completed ON")
    second_quote_receipt_on = fields.Date(string="Second Quote Receipt ON")
    loi_issued_on = fields.Date(string="LOI Issued ON")
    tr_proposal_submitted_on = fields.Date(string="TR Proposal Submitted ON")

    # relations
    requisition_id = fields.Many2one("material.purchase.requisition", string="Requisition")

    def update(self):
        """
        This method update value in PR.
        """
        print(self, '==========================self')
        self.requisition_id.pr_accept_date = self.pr_accept_date
        self.requisition_id.tr_approved_on = self.tr_approved_on
        self.requisition_id.bid_list_approved_date = self.bid_list_approved_date
        self.requisition_id.target_price_sent_on = self.target_price_sent_on
        self.requisition_id.rfq_sent_on = self.rfq_sent_on
        self.requisition_id.final_quote_receipt = self.final_quote_receipt
        self.requisition_id.first_quote_receipt_on = self.first_quote_receipt_on
        self.requisition_id.sourcing_completed_on = self.sourcing_completed_on
        self.requisition_id.second_quote_receipt_on = self.second_quote_receipt_on
        self.requisition_id.loi_issued_on = self.loi_issued_on
        self.requisition_id.tr_proposal_submitted_on = self.tr_proposal_submitted_on
        return True
