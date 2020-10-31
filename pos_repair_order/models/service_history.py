# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ServiceHistory(models.Model):
    _name = 'service.history'
    _description = 'Service History'
    _rec_name = 'label'

    # attributes
    label = fields.Char('Label')
    action_time = fields.Datetime('Action Datetime')
    action_remark = fields.Text('Action Remark')
    user_id = fields.Many2one('res.users', 'User')

    # relations
    repair_ord_history_id = fields.Many2one('repair.order')


class HoldReason(models.Model):
    _name = 'hold.reason'
    _description = 'Hold Reason'
    _rec_name = 'name'

    # attributes
    name = fields.Char('Name', required=True)

class FuelType(models.Model):
    _name = 'fuel.type'
    _description = 'Fuel Type'
    _rec_name = 'fuel_type'

    # attributes
    fuel_type = fields.Char('Fuel Type')