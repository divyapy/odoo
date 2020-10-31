# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError


class CreateSingleSource(models.TransientModel):
    _name = 'wiz.create.single.source'
    _description = 'Create Single Source'

    # relations
    requisition_id = fields.Many2one('material.purchase.requisition', string="Requisition")
    vendor_id = fields.Many2one('res.partner', string='Proposed Vendor Name', required=True)

    def create_single_source(self):
        """
        This method Creates Single Source.
        """
        single_source_id = self.env['single.source.configuration'].create({
            'pr_id': self.requisition_id.id,
            'department_id': self.requisition_id.department_id.id,
            'vendor_id': self.vendor_id.id,
        })
        self.requisition_id.single_source_id = single_source_id
        for line in self.requisition_id.requisition_line_ids:
            self.env['single.source.line'].create({
                'source_id':single_source_id.id,
                'product_id': line.product_id.id,
                'description': line.description,
                'qty': line.qty,
                'uom': line.uom.id,
                'unit_price': line.unit_price,
                'sub_total': line.sub_total,
            })
        return True
