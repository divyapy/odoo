# -*- coding: utf-8 -*-

import base64

from odoo import api, fields, models, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _force_picking_done(self, picking):
        """Force picking in order to be set as done."""
        self.ensure_one()
        picking.action_assign()
        pos_order_obj = self.env['pos.order'].search([('name', '=', picking.origin)])
        if pos_order_obj.session_id.config_id.po_stock_transfer:
            wrong_lots = self.set_pack_operation_lot(picking)
            if not wrong_lots:
                picking.action_done()

    def cal_string(self, string):
        """
        This function returns list of string to POS OrderReceipt by splitting with '\n'.
        """
        output = string.split("\n")
        return output


    @api.model
    def create_from_ui(self, orders, draft=False):
        print(orders, '++++++++++')
        order = []
        if type(orders) == dict:
            print('=========Iamherelolist', orders)
            order.append(orders)
            orders = order
        res = super(PosOrder, self).create_from_ui(orders, draft)
        return res        

    @api.model
    def action_receipt_to_customer(self, name, client, ticket, order_ids=False):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            return False
        if not client.get('email'):
            return False
        orders = self.browse(order_ids) if order_ids else self

        message = _("<p>Dear %s,<br/>Here is your electronic ticket for the %s. </p>") % (client['name'], name)
        template_data = {
            'subject': _('Receipt %s') % name,
            'body_html': message,
            'author_id': self.env.user.partner_id.id,
            'email_from': self.env.company.email or self.env.user.email_formatted,
            'email_to': client['email']
        }

        if orders.mapped('account_move'):
            report = self.env.ref('point_of_sale.pos_invoice_report').render_qweb_pdf(orders.ids[0])
            filename = name + '.pdf'
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(report[0]),
                'store_fname': filename,
                'res_model': 'account.move',
                'res_id': order_ids[0],
                'mimetype': 'application/x-pdf'
            })
            template_data['attachment_ids'] = attachment

        mail = self.env['mail.mail'].create(template_data)
        mail.send()

    def action_pos_order_paid(self):
        """
        """
        if not float_is_zero(self.amount_total - self.amount_paid, precision_rounding=self.currency_id.rounding):
            raise UserError(_("Order %s is not fully paid.") % self.name)
        self.write({'state': 'paid'})
        # if not self.session_id.config_id.auto_repair_order_transfer and not self.session_id.config_id.repair_order_op_type:
        if(not self.session_id.config_id.auto_repair_order_transfer and not self.session_id.config_id.repair_order_op_type) or not self.repair_id:
            return self.create_picking()