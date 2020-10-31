##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models,fields,api, _
from ast import literal_eval
from odoo.exceptions import Warning, UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    #RFQ Attachment
    attachment_ids = fields.One2many('purchase.order.attachment.line','po_id', string='Attachment IDS')
        

    @api.model
    def default_get(self, fields):
        res = super(PurchaseOrder, self).default_get(fields)
        attachment_type_lines = []
        attachment_type_ids = self.env['attachment.type'].search([('attachment_type', '=', 'rfq')])

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
        res = super(PurchaseOrder, self).write(vals)
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



class PurchaseOrderAttachmentLine(models.Model):
    _name = "purchase.order.attachment.line"
    _description = 'Purchase Order Attachment Lines'

    po_id = fields.Many2one('purchase.order', string='Purchase Order ID')

    #Sourcing Attachment
    attachment_type_id = fields.Many2one('attachment.type', string='Type')
    attachment_status_id = fields.Many2one('attachment.status', string='Status')
    move_next_level = fields.Boolean(string='Move to Next Level')
    attachment_file = fields.Binary(string="Attachment", attachment=True)
    is_mandatory = fields.Boolean(related='attachment_type_id.is_mandatory',string='Mandatory')