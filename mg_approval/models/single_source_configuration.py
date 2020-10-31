# -*- coding: utf-8 -*-

from odoo import fields, models, tools, api, _
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError


class SingleSourceConfiguration(models.Model):
    _name = 'single.source.configuration'
    _description = 'Single Source Configuration'
    _rec_name = 'pr_no'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # attributes
    department_id = fields.Many2one("hr.department", string="Project / Dept Name")
    pr_no = fields.Char(string='Number', index=True, readonly=1)
    pr_amount = fields.Float(string="PR Amount")
    pr_desp = fields.Text(string="Project Description")
    vendor_phone = fields.Char(string="Phone", related="vendor_id.phone")
    vendor_email = fields.Char(string="Email", related="vendor_id.email")

    # relations
    pr_id = fields.Many2one('material.purchase.requisition', string='Purchase Requisition ID')
    vendor_id = fields.Many2one("res.partner", string="Proposed Vendor Name")
    config_id = fields.Many2one("single.source.request.config", string="Source Category")
    config_ids = fields.One2many("source.configs", 'configs_id', string="Configs")
    single_source_line_ids = fields.One2many(
        'single.source.line',
        'source_id',
        string='Single Source Line',
        copy=True,
    )

    category_id = fields.Many2one("procurement.approval.category", string="Approval Category")
    request_status = fields.Selection([
        ('new', 'To Submit'),
        ('pending', 'Submitted'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], default="new", compute="_compute_request_status", store=True, compute_sudo=True, group_expand='_read_group_request_status')
    request_owner_id = fields.Many2one('res.users', string="Request Owner")
    user_status = fields.Selection([
        ('new', 'New'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], compute="_compute_user_status")
    has_access_to_request = fields.Boolean(string="Has Access To Request", compute="_compute_has_access_to_request")
    approval_minimum = fields.Integer(related="category_id.approval_minimum")
    is_manager_approver = fields.Boolean(related="category_id.is_manager_approver")
    approver_ids = fields.One2many("single.source.approval.approver", "request_id", string="Approvers")

    def _compute_has_access_to_request(self):
        is_approval_user = self.env.user.has_group('mg_approval.group_procurement_approval_user')
        for request in self:
            request.has_access_to_request = request.request_owner_id == self.env.user and is_approval_user

    def action_confirm(self):
        if len(self.approver_ids) < self.approval_minimum:
            raise UserError(_("You have to add at least %s approvers to confirm your request.") % self.approval_minimum)
        approvers = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'new')
        approvers.write({'status': 'pending'})

    def action_approve(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'approved'})
        # self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()

    def action_refuse(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'refused'})
        # self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()

    def action_withdraw(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'pending'})

    def action_draft(self):
        self.mapped('approver_ids').write({'status': 'new'})

    def action_cancel(self):
        # self.sudo()._get_user_approval_activities(user=self.env.user).unlink()
        self.mapped('approver_ids').write({'status': 'cancel'})

    @api.depends('approver_ids.status')
    def _compute_user_status(self):
        for approval in self:
            approval.user_status = approval.approver_ids.filtered(lambda approver: approver.user_id == self.env.user).status

    @api.depends('approver_ids.status')
    def _compute_request_status(self):
        for request in self:
            status_lst = request.mapped('approver_ids.status')
            minimal_approver = request.approval_minimum if len(status_lst) >= request.approval_minimum else len(status_lst)
            if status_lst:
                if status_lst.count('cancel'):
                    status = 'cancel'
                elif status_lst.count('refused'):
                    status = 'refused'
                elif status_lst.count('new'):
                    status = 'new'
                elif status_lst.count('approved') >= minimal_approver:
                    status = 'approved'
                else:
                    status = 'pending'
            else:
                status = 'new'
            request.request_status = status

    @api.onchange('category_id', 'request_owner_id')
    def _onchange_category_id(self):
        current_users = self.approver_ids.mapped('user_id')
        new_users = self.category_id.user_ids
        if self.category_id.is_manager_approver:
            employee = self.env['hr.employee'].search([('user_id', '=', self.request_owner_id.id)], limit=1)
            if employee.parent_id.user_id:
                new_users |= employee.parent_id.user_id
        for user in new_users - current_users:
            self.approver_ids += self.env['single.source.approval.approver'].new({
                'user_id': user.id,
                'request_id': self.id,
                'status': 'new'})

    def _write(self, values):
        # The attribute 'tracking' doesn't work for the
        # field request_status, as it is updated from the client side
        # We have to track the values modification by hand.
        if values.get('request_status'):
            # The compute method is already called and the new value is in cache.
            # We have to retrieve the correct old value from the database, as it is
            # stored computed field.
            self.env.cr.execute("""SELECT id, request_status FROM single_source_configuration WHERE id IN %s""", (tuple(self.ids),))
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
        return super(SingleSourceConfiguration, self)._write(values)

    def create_po(self):
        """
        """
        return

    @api.model
    def create(self, vals):
        pr_no = self.env['ir.sequence'].next_by_code('single.source.configuration.seq')
        vals.update({
            'pr_no': pr_no
        })
        res = super(SingleSourceConfiguration, self).create(vals)
        return res

    @api.onchange('config_id')
    def fill_configs(self):
        """
        """
        data = []
        if self.config_id:
            for objs in self.config_id.config_ids:
                obj = self.env['source.configs'].create({
                    'name': objs.name,
                    'select': objs.select,
                    'configs_id': self.id
                })
                data.append(obj.id)
            self.config_ids = [(6, 0, data)]
        return

class SingleSourceRequestConfig(models.Model):
    _name = 'single.source.request.config'
    _description = 'Single Source Request Config'
    _rec_name = 'name'

    # attributes
    name = fields.Char(string="Name")
    config_ids = fields.One2many("source.configs", 'config_id', string="Configs")

class SourceConfigs(models.Model):
    _name = 'source.configs'
    _description = 'Single Source Request Config'
    _rec_name = 'name'

    # attributes
    select = fields.Selection([('yes', 'Yes'),('no', 'No')], string="Select")
    name = fields.Char(string="Name")

    # relations
    config_id = fields.Many2one('single.source.request.config')
    configs_id =  fields.Many2one('single.source.configuration')


class SingleSourceConfigurationLine(models.Model):
    _name = "single.source.line"
    _description = 'Single Source Configuration Line'


    source_id = fields.Many2one(
        'single.source.configuration',
        string='Requisitions',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
    description = fields.Char(
        string='Description',
        required=True,
    )
    qty = fields.Float(
        string='Quantity',
        default=1,
        required=True,
    )
    uom = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
    )    
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
            sub_total = rec.qty * rec.unit_price
            rec.sub_total = sub_total


class SingleSourceApprovalApprover(models.Model):
    _name = 'single.source.approval.approver'
    _description = 'Single Source Approver'

    user_id = fields.Many2one('res.users', string="User", required=True)
    status = fields.Selection([
        ('new', 'New'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], string="Status", default="new", readonly=True)
    request_id = fields.Many2one('single.source.configuration', string="Request", ondelete='cascade')

    def action_approve(self):
        self.request_id.action_approve(self)

    def action_refuse(self):
        self.request_id.action_refuse(self)

    @api.onchange('user_id')
    def _onchange_approver_ids(self):
        return {'domain': {'user_id': [('id', 'not in', self.request_id.approver_ids.mapped('user_id').ids + self.request_id.request_owner_id.ids)]}}
