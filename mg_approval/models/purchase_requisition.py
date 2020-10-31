# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError


class MaterialPurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    mpr_id = fields.Many2one('material.purchase.requisition', string="Purchase Requisition", copy=False, readonly=True)
    
    #RFQ Attachment
    attachment_ids = fields.One2many('purchase.requisition.attachment.line','pr_id', string='Attachment IDS')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.company.currency_id.id)


    @api.depends('line_ids.sub_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = 0.0
            for line in order.line_ids:
                amount_untaxed += line.sub_total
            order.update({
                'amount_total': amount_untaxed
            })


    def open_mpr(self,):
        return {
            'name': _('%s' % self.mpr_id.name),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('mg_approval.material_purchase_requisition2_inherit_form_view').id,
            'res_model': 'material.purchase.requisition',
            'res_id': self.mpr_id.id
        }
    
    @api.model
    def default_get(self, fields):
        res = super(MaterialPurchaseRequisition, self).default_get(fields)
        attachment_type_lines = []
        attachment_type_ids = self.env['attachment.type'].search([('attachment_type', '=', 'sourcing')])

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


class PurchaseRequisitionAttachmentLine(models.Model):
    _name = "purchase.requisition.attachment.line"
    _description = 'Purchase Requisition Attachment Lines'

    pr_id = fields.Many2one('purchase.requisition', string='Purchase Requisition ID')

    #Sourcing Attachment
    attachment_type_id = fields.Many2one('attachment.type', string='Type')
    attachment_status_id = fields.Many2one('attachment.status', string='Status')
    move_next_level = fields.Boolean(string='Move to Next Level')
    attachment_file = fields.Binary(string="Attachment", attachment=True)
    is_mandatory = fields.Boolean(related='attachment_type_id.is_mandatory',string='Mandatory')


class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    sub_total = fields.Float(
        string='Subtotal',
        default=0.00,
        required=True,
    )

    @api.onchange('product_id')
    def onchange_product_id(self):
        for rec in self:
            rec.price_unit = rec.product_id.standard_price
            rec.sub_total = rec.product_qty * rec.price_unit

    @api.onchange('unit_price')
    def onchange_unit_price(self):
        for rec in self:
            rec.sub_total = rec.product_qty * rec.price_unit

    @api.onchange('qty')
    def onchange_qty(self):
        for rec in self:
            rec.sub_total = rec.product_qty * rec.price_unit