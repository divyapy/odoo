# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError


class MaterialPurchaseRequisition(models.TransientModel):
    _name = 'wiz.create.tender'

    pr_type_id = fields.Many2one('purchase.requisition.type', string="Sourcing Document Type", required=True)

    def create_sourcing(self,):
        ctx = self._context
        mpr = self.env['material.purchase.requisition'].search([('id', '=', ctx.get('active_id'))])
        print (mpr)
        vals = {
                'schedule_date': mpr.date_end,
                'type_id': self.pr_type_id and self.pr_type_id.id or False,
                'company_id': mpr.company_id.id,
                'state': 'draft',
                'mpr_id': mpr.id
            }
        user_id = self._uid
        responsible_id = mpr.requisiton_responsible_id
        if responsible_id and responsible_id.user_id:
            user_id = responsible_id.user_id.id
        vals['user_id'] = user_id
        line_ids = []
        for l in mpr.requisition_line_ids:
            qty = l.qty
            line_ids.append((0, 0, {
                'product_id': l.product_id.id,
                'product_qty': qty,
                'qty_ordered': qty,
                'price_unit':l.unit_price,
                'product_uom_id':l.product_id.uom_id.id,
                'sub_total':l.sub_total
                }))
        vals['line_ids'] = line_ids
        sup_ids = []
        for sup_id in mpr.recommended_potentail_supplier_ids.filtered(lambda l: l.vendor_id):
            sup_ids.append((0, 0, {
                'supplier_name': sup_id.vendor_id.id,
                }))
        vals['pr1_bid_ids'] = sup_ids
        print(vals)
        pr = self.env['purchase.requisition'].create(vals)
        for bid_id in pr.pr1_bid_ids:
            bid_id._onchange_supplier_name()
        mpr.state = 'sourcing_created'
        mpr.pr_id = pr.id
        return True
