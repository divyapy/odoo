# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class PODetailsWizard(models.TransientModel):
    _name = 'po.details.wizard'
    _description = 'PO Details'

    po_dt_po_number = fields.Char(string="PO Number")
    po_dt_supplier_name = fields.Char(string="Supplier Name")
    po_dt_vendor_code = fields.Char(string="Vendor Code")
    po_dt_pr_amount = fields.Float(string="PR Amount")
    po_dt_issue_date = fields.Date(string="Issue Date")
    po_dt_end_date = fields.Date(string="End Date")
    po_dt_delivery_date = fields.Date(string="Delivery Date")
    po_dt_biq = fields.Float(string="BIQ (Best Initial Quote)")
    po_dt_saveing_from_biq = fields.Float(string="Saving from BIQ")
    po_dt_remarks = fields.Text(string="Remarks")

    # relations
    requisition_id = fields.Many2one("material.purchase.requisition", string="Requisition")

    def update(self):
        """
        This method update value in PR.
        """
        self.requisition_id.po_dt_po_number = self.po_dt_po_number
        self.requisition_id.po_dt_supplier_name = self.po_dt_supplier_name
        self.requisition_id.po_dt_vendor_code = self.po_dt_vendor_code
        self.requisition_id.po_dt_pr_amount = self.po_dt_pr_amount
        self.requisition_id.po_dt_issue_date = self.po_dt_issue_date
        self.requisition_id.po_dt_end_date = self.po_dt_end_date
        self.requisition_id.po_dt_delivery_date = self.po_dt_delivery_date
        self.requisition_id.po_dt_biq = self.po_dt_biq
        self.requisition_id.po_dt_saveing_from_biq = self.po_dt_saveing_from_biq
        self.requisition_id.po_dt_remarks = self.po_dt_remarks
        return True
