# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class AccountBankStatmentLine(models.Model):
    _inherit = 'account.bank.statement.line'

    # relations
    repair_ord_pymt_id = fields.Many2one('repair.order')
    cashier_id = fields.Many2one('res.users', 'Cashier')