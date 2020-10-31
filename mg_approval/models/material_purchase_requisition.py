# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import Warning, UserError

class MaterialPurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'

    # attributes
    initiator_id = fields.Many2one("res.users", string="Initiator")
    # depratment = fields.Char(string="Department")
    phone = fields.Char(string="Contact Number", related="initiator_id.partner_id.phone", store=True)
    plant_location = fields.Char(string="Plant/Location")
    cost_center = fields.Char(string="Cost Center")
    gl_account = fields.Char(string="G/L Account")
    ar_number = fields.Char(string="AR Number")
    wbs_element = fields.Char(string="WBS Element")
    is_project_pr = fields.Selection([('yes', 'Yes'),('no', 'No')], default='no',
        string="Is Project PR?")
    program_code = fields.Char(string="Program Code")
    is_nda_required = fields.Selection([('yes', 'Yes'),('no', 'No')], default='no',
        string="Is NDA Required ?")
    po_required = fields.Selection([('yes', 'Yes'),('no', 'No')], default='no',
        string="PO Required ?")
    no_po_reason = fields.Text(string="NO PO Reason")
    single_source_type = fields.Char(string="Single Source Type")
    pr_number = fields.Char(string='PR Number', index=True, readonly=1)
    pr_date = fields.Date(string="PR Date")
    tentative_date = fields.Date(string="Tentative Date Required")
    pr_type = fields.Char(string="PR Type")
    sub_type = fields.Char(string="Sub Type")
    # pr_category = fields.Char(string="PR Category") # Need replace by category_id
    budgeted_item = fields.Selection([('yes', 'Yes'),('no', 'No')], default='no',
        string="Budgeted Item")
    year = fields.Char(string="Year")
    budgeted_line_item = fields.Char(string="Budgeted Line Item")
    is_hazardous = fields.Selection([('yes', 'Yes'),('no', 'No')], default='no',
        string="Is Hazardous ?")
    is_single_source = fields.Selection([('yes', 'Yes'),('no', 'No')], default='no',
        string="Is Single Source ?")
    purchase_negotiation_required = fields.Selection([('yes', 'Yes'),('no', 'No')], default='no',
        string="Purchase Negotiation Required ?")
    pr_receipt_date = fields.Date(string="PR Receipt Date")
    # forward_to_buyer = fields.Many2one("hr.employee", string="Forward to Buyer", tracking=True)
    supplier_name = fields.Char(string="Supplier Name")
    vendor_code = fields.Char(string="Vendor Code")
    po_number = fields.Char(string="PO Number")
    po_amount = fields.Float(string="PO Amount")
    po_invoice_date = fields.Date(string="PO Invoice Date")
    po_end_date = fields.Date(string="PO End Date")
    delivery_date = fields.Date(string="Delivery Date")
    biq = fields.Char(string="BIQ (Best Initial Quote)")
    savings_from_biq = fields.Char(string="")
    close_pr = fields.Selection([('yes', 'Yes'),('no', 'No')], default='no', string="Close PR ?")

    # relations
    pr_curreny_id = fields.Many2one("res.currency", string="PR Currency")
    single_source_id = fields.Many2one('single.source.configuration', string='Single Source ID')

    # Extra
    category_id = fields.Many2one("procurement.approval.category", string="PR Category")
    approver_ids = fields.One2many("procurement.approval.approver", "request_id", string="Approvers")
    recommended_potentail_supplier_ids = fields.One2many("recommended.potentail.supplier", "requisition_id", string="Recommended Potential Suppliers")
    request_owner_id = fields.Many2one('res.users', string="Request Owner")
    has_access_to_request = fields.Boolean(string="Has Access To Request", compute="_compute_has_access_to_request")
    request_status = fields.Selection([
        ('new', 'To Submit'),
        ('pending', 'Submitted'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], default="new", compute="_compute_request_status", store=True, compute_sudo=True, group_expand='_read_group_request_status')
    user_status = fields.Selection([
        ('new', 'New'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], compute="_compute_user_status")
    approval_minimum = fields.Integer(related="category_id.approval_minimum")
    is_manager_approver = fields.Boolean(related="category_id.is_manager_approver")

    # Purchase Action Dashboard
    pr_accept_date = fields.Date(string="PR Accept Date", tracking=True)
    tr_approved_on = fields.Date(string="TR Approved ON", tracking=True)
    bid_list_approved_date = fields.Date(string="Bid List Approve Date", tracking=True)
    target_price_sent_on = fields.Date(string="Target Price Send ON", tracking=True)
    rfq_sent_on = fields.Date(string="RFQ Sent ON", tracking=True)
    final_quote_receipt = fields.Char(string="Final Quote Receipt", tracking=True)
    first_quote_receipt_on = fields.Date(string="First Quote Receipt ON", tracking=True)
    sourcing_completed_on = fields.Date(string="Sourcing Completed ON", tracking=True)
    second_quote_receipt_on = fields.Date(string="Second Quote Receipt ON", tracking=True)
    loi_issued_on = fields.Date(string="LOI Issued ON", tracking=True)
    tr_proposal_submitted_on = fields.Date(string="TR Proposal Submitted ON", tracking=True)

    # PO Details
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

    #PR Attachment
    attachment_ids = fields.One2many('material.purchase.attachment.line','requisition_id', string='Attachment IDS')

    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.company.currency_id.id)
    ##
    requisiton_responsible_id = fields.Many2one(
        'hr.employee',
        string='Requisition Responsible',
        copy=True,
        tracking=True
    )
    state = fields.Selection(selection=[
        ('draft', 'New'),
        ('dept_confirm', 'Waiting Department Approval'),
        ('ir_approve', 'Waiting IR Approval'),
        ('approve', 'Approved'),
        ('stock', 'Purchase Order Created'),
        ('receive', 'Received'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected'),
        ('pending', 'Waiting Approval')],
        default='draft',
        index=True,
        track_visibility='onchange',
    )
    
    @api.depends('requisition_line_ids.sub_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = 0.0
            for line in order.requisition_line_ids:
                amount_untaxed += line.sub_total
            order.update({
                'amount_total': amount_untaxed
            })

    def _compute_has_access_to_request(self):
        is_approval_user = self.env.user.has_group('mg_approval.group_procurement_approval_user')
        for request in self:
            request.has_access_to_request = request.request_owner_id == self.env.user and is_approval_user

    @api.onchange('category_id', 'request_owner_id')
    def _onchange_category_id(self):
        current_users = self.approver_ids.mapped('user_id')
        print(current_users, '============current_users======')
        new_users = self.category_id.user_ids
        print(new_users, '=========new_users')
        if self.category_id.is_manager_approver:
            employee = self.env['hr.employee'].search([('user_id', '=', self.request_owner_id.id)], limit=1)
            if employee.parent_id.user_id:
                new_users |= employee.parent_id.user_id
        objs = []
        for user in new_users - current_users:
            print(user, '==================user=============', user.id)
            obj = self.env['procurement.approval.approver'].create({
                'user_id': user.id,
                'request_id': self.id,
                'status': 'new'
            })
            print(obj, '===============objs')
            objs.append(obj.id)
            print(objs, '=================objs')
            print(self.approver_ids, '=============')
            self.approver_ids = [(6, 0, objs)]

    @api.depends('approver_ids.status')
    def _compute_request_status(self):
        for request in self:
            status_lst = request.mapped('approver_ids.status')
            minimal_approver = request.approval_minimum if len(status_lst) >= request.approval_minimum else len(status_lst)
            print(status_lst, '==========status_lst============')
            print(minimal_approver, '==========minimal_approver')
            print(status_lst.count('approved'), '======================')
            if status_lst:
                print('=============if')
                if status_lst.count('approved') >= minimal_approver:
                    status = 'approved'
                elif status_lst.count('cancel') >= minimal_approver:
                    status = 'cancel'
                elif status_lst.count('refused') >= minimal_approver:
                    status = 'refused'
                elif status_lst.count('new'):
                    status = 'new'
                else:
                    status = 'pending'
            else:
                print('=============else')
                status = 'new'
            print(status, '===============status_lst')
            request.request_status = status
            print(request, '==========request')
            if status == 'approved':
                request.state = 'approve'
            if status == 'refused':
                request.state = 'reject'
            if status == 'cancel':
                request.state = 'cancel'
            if status == 'pending':
                request.state = 'pending'

    @api.depends('approver_ids.status')
    def _compute_user_status(self):
        for approval in self:
            approval.user_status = approval.approver_ids.filtered(lambda approver: approver.user_id == self.env.user).status

    def _write(self, values):
        # The attribute 'tracking' doesn't work for the
        # field request_status, as it is updated from the client side
        # We have to track the values modification by hand.
        if values.get('request_status'):
            # The compute method is already called and the new value is in cache.
            # We have to retrieve the correct old value from the database, as it is
            # stored computed field.
            self.env.cr.execute("""SELECT id, request_status FROM material_purchase_requisition WHERE id IN %s""", (tuple(self.ids),))
            mapped_data = {data.get('id'): data.get('request_status') for data in self.env.cr.dictfetchall()}
            for request in self:
                old_value = mapped_data.get(request.id)
                if old_value != values['request_status']:
                    selection_description_values = {elem[0]: elem[1] for elem in self._fields['request_status']._description_selection(self.env)}
                    request._message_log(body=_('State change.'), tracking_value_ids=[(0, 0, {
                        'field': 'request_status',
                        'field_desc': 'Request Status',
                        'field_type': 'selection',
                        'old_value_char': selection_description_values.get(old_value),
                        'new_value_char': selection_description_values.get(values['request_status']),
                    })])
                    if request.request_owner_id:
                        request.message_notify(
                            partner_ids=request.request_owner_id.partner_id.ids,
                            body=_("Your request %s is now in the state %s") % (request.name, selection_description_values.get(values['request_status'])),
                            subject=request.name)
        return super(MaterialPurchaseRequisition, self)._write(values)

    def dashboard(self):
        """
        """
        self.ensure_one()
        ctx = dict(
            default_model = 'material.purchase.requisition',
            default_requisition_id = self.id,
            default_pr_accept_date = self.pr_accept_date,
            default_tr_approved_on = self.tr_approved_on,
            default_bid_list_approved_date = self.bid_list_approved_date,
            default_target_price_sent_on = self.target_price_sent_on,
            default_rfq_sent_on = self.rfq_sent_on,
            default_final_quote_receipt = self.final_quote_receipt,
            default_first_quote_receipt_on = self.first_quote_receipt_on,
            default_sourcing_completed_on = self.sourcing_completed_on,
            default_second_quote_receipt_on = self.second_quote_receipt_on,
            default_loi_issued_on = self.loi_issued_on,
            default_tr_proposal_submitted_on = self.tr_proposal_submitted_on,

        )
        return {
            'name': _('Purchase Action Dashboard'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'purchase.action.dashboard.wizard',
            'target': 'new',
            'context': ctx
        }

    def edit_po_details(self):
        """
        """
        self.ensure_one()
        ctx = dict(
            default_model = 'material.purchase.requisition',
            default_requisition_id = self.id,
            default_po_dt_po_number = self.po_dt_po_number,
            default_po_dt_supplier_name = self.po_dt_supplier_name,
            default_po_dt_vendor_code = self.po_dt_vendor_code,
            default_po_dt_pr_amount = self.po_dt_pr_amount,
            default_po_dt_issue_date = self.po_dt_issue_date,
            default_po_dt_end_date = self.po_dt_end_date,
            default_po_dt_delivery_date = self.po_dt_delivery_date,
            default_po_dt_biq = self.po_dt_biq,
            default_po_dt_saveing_from_biq = self.po_dt_saveing_from_biq,
            default_po_dt_remarks = self.po_dt_remarks,

        )
        return {
            'name': _('PO Details'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'po.details.wizard',
            'target': 'new',
            'context': ctx
        }

    def action_pr_approve(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'approved'})

    def action_pr_refuse(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'refused'})

    def action_pr_withdraw(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'pending'})

    def reset_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.mapped('approver_ids').write({'status': 'new'})

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
            rec.mapped('approver_ids').write({'status': 'cancel'})

    def action_pr_confirm(self):
        if len(self.approver_ids) < self.approval_minimum:
            raise UserError(_("You have to add at least %s approvers to confirm your request.") % self.approval_minimum)
        # if self.requirer_document == 'required' and not self.attachment_number:
            # raise UserError(_("You have to attach at lease one document."))
        approvers = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'new')
        # approvers._create_activity()
        approvers.write({'status': 'pending'})
        self.state = 'pending'
        # self.write({'date_confirmed': fields.Datetime.now()})

    def action_show_documents(self):
        """
        This method show attached document with
        PR.
        """
        ids = []
        approver = self.mapped('approver_ids').filtered(
            lambda approver: approver.user_id == self.env.user
        )
        print(approver, '==============approver')
        print(approver.approve_attachment_id,'===========approve_attachment_id')
        print(approver.refused_attachment_id,'===========refused_attachment_id')
        print(approver.cancel_attachment_id,'===========cancel_attachment_id')

        if approver.approve_attachment_id:
            ids.append(approver.approve_attachment_id.id)
        if approver.refused_attachment_id:
            ids.append(approver.refused_attachment_id.id)
        if approver.cancel_attachment_id:
            ids.append(approver.cancel_attachment_id.id)
        print(ids, '==============ids')
        return {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_id': False,
            'res_model': 'ir.attachment',
            'domain': [('id', 'in', ids)]
        }

    def action_show_all_documents(self):
        """
            This method show all attached document with
            PR.
        """
        ids = []
        approvers = self.mapped('approver_ids')
        for approver in approvers:
            if approver.approve_attachment_id:
                ids.append(approver.approve_attachment_id.id)
            if approver.refused_attachment_id:
                ids.append(approver.refused_attachment_id.id)
            if approver.cancel_attachment_id:
                ids.append(approver.cancel_attachment_id.id)
        return {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_id': False,
            'res_model': 'ir.attachment',
            'domain': [('id', 'in', ids)]
        }

    def action_show_single_source(self):
        """
        This method show Single Sources for
        PR.
        """
        return {
            'name': ("Single Sources"),
            'type': 'ir.actions.act_window',
            'res_model': 'single.source.configuration',
            'view_mode': 'tree,form',
            'domain': [('pr_id', '=', self.id)],
        }

    @api.model
    def default_get(self, fields):
        res = super(MaterialPurchaseRequisition, self).default_get(fields)
        attachment_type_lines = []
        attachment_type_ids = self.env['attachment.type'].search([('attachment_type', '=', 'pr')])

        for attachment_types in attachment_type_ids:
            line = (0,0,{
                'attachment_type_id' : attachment_types.id,
                'is_mandatory':attachment_types.is_mandatory
            })
            attachment_type_lines.append(line)
        res.update({
            'attachment_ids' : attachment_type_lines
        })
        return res


    def write(self, vals):
        res = super(MaterialPurchaseRequisition, self).write(vals)
        if self.attachment_ids:
            name = ""
            count = 0
            for attachment_id in self.attachment_ids:
                if not attachment_id.attachment_file and  attachment_id.is_mandatory == True:
                    if count !=0:
                        name += ", "
                    name += str(attachment_id.attachment_type_id.name)
                    count+=1
            if count > 0:
                raise UserError(_("You have to add attachment for %s") % name)
        return res

class ProcurementApprovalApprover(models.Model):
    _name = 'procurement.approval.approver'
    _description = 'Procurement Approver'

    user_id = fields.Many2one('res.users', string="User") # , required=True
    status = fields.Selection([
        ('new', 'New'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], string="Status", default="new", readonly=True, tracking=True)
    request_id = fields.Many2one('material.purchase.requisition', string="Request", ondelete='cascade')
    approve_attachment_id = fields.Many2one("ir.attachment", string="Approve Attachment", attachment=True)
    approve_comments = fields.Text(string="Approve Comments")
    approve_rework = fields.Text(string="Approve Rework")
    refused_attachment_id = fields.Many2one("ir.attachment", string="Refused Attachment", attachment=True)
    refused_comments = fields.Text(string="Refused Comments")
    refused_rework = fields.Text(string="Refused Rework")
    cancel_attachment_id = fields.Many2one("ir.attachment", string="Cancel Attachment", attachment=True)
    cancel_comments = fields.Text(string="Cancel Comments")
    cancel_rework = fields.Text(string="Cancel Rework")

    def action_approve(self):
        self.request_id.action_approve(self)

    def action_refuse(self):
        self.request_id.action_refuse(self)

    @api.onchange('user_id')
    def _onchange_approver_ids(self):
        return {'domain': {'user_id': [('id', 'not in', self.request_id.approver_ids.mapped('user_id').ids + self.request_id.request_owner_id.ids)]}}


class RecommendedPotentailSupplier(models.Model):
    _name = 'recommended.potentail.supplier'
    _description = 'Recommended Potentail Supplier'

    # attributes
    vendor_phone = fields.Char(related="vendor_id.phone", string="Phone", store=True)
    vendor_email = fields.Char(related="vendor_id.email", string="Email", store=True)
    vendor_fax = fields.Char(string="Fax Number")
    vendor_code = fields.Char(string="Vendor Code")
    vendor_gstin =  fields.Char(string="GSTIN Number")
    contact_person = fields.Char(string="Contact Person")
    address = fields.Char(compute="_combine_address", store=True)

    # relations
    vendor_id = fields.Many2one("res.partner", string="Vendor")
    requisition_id = fields.Many2one('material.purchase.requisition', string="Request")

    @api.depends('vendor_id')
    def _combine_address(self):
        """
        """
        for res in self:
            address = ''
            address += ( res.vendor_id.city + ' ')  if res.vendor_id.city else ' '
            address += ( res.vendor_id.state_id.name + ' ') if res.vendor_id.state_id else ' '
            address += ( res.vendor_id.street + ' ') if res.vendor_id.street else ' '
            address += ( res.vendor_id.street2 + ' ') if res.vendor_id.street2 else ' '
            address += ( res.vendor_id.zip + ' ') if res.vendor_id.zip else ' '
            address += ( res.vendor_id.country_id.name + ' ') if res.vendor_id.country_id else ' '
            res.address = address

class MaterialPurchaseRequisitionLine(models.Model):
    _inherit = 'material.purchase.requisition.line'


    unit_price = fields.Float(
        string='Unit Price',
        default=0.00,
        required=True,
    )
    sub_total = fields.Float(
        string='Subtotal',
        default=0.00,
        required=True,
    )

    @api.onchange('product_id')
    def onchange_product_id(self):
        for rec in self:
            rec.description = rec.product_id.name
            rec.uom = rec.product_id.uom_id.id
            rec.unit_price = rec.product_id.standard_price
            rec.sub_total = rec.qty * rec.unit_price

    @api.onchange('unit_price')
    def onchange_unit_price(self):
        for rec in self:
            rec.sub_total = rec.qty * rec.unit_price

    @api.onchange('qty')
    def onchange_qty(self):
        for rec in self:
            rec.sub_total = rec.qty * rec.unit_price

class MaterialPurchaseAttachmentLine(models.Model):
    _name = "material.purchase.attachment.line"
    _description = 'Material Purchase Attachment Lines'

    requisition_id = fields.Many2one('material.purchase.requisition', string='Requisition ID')

    #PR Attachment
    attachment_type_id = fields.Many2one('attachment.type', string='Type')
    attachment_status_id = fields.Many2one('attachment.status', string='Status')
    move_next_level = fields.Boolean(string='Move to Next Level')
    attachment_file = fields.Binary(string="Attachment", attachment=True)
    is_mandatory = fields.Boolean(related='attachment_type_id.is_mandatory',string='Mandatory')
