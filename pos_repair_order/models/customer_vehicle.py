# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class CustomerVehicleBrand(models.Model):
    _name = 'customer.vehicle.brand'
    _description = 'Customer Vehicle Brand'
    _rec_name = 'brand_name'

    # attributes
    brand_name = fields.Char("Brand Name", required=True)

    _sql_constraints = [
        ('code_brand_nameq', 'unique (brand_name)', 'The brand name must be unique per record !'),
    ]


class CustomerVehicleModel(models.Model):
    _name = 'customer.vehicle.model'
    _description = 'Customer Vehicle Model'
    _rec_name = 'model_name'

    # attributes
    model_name = fields.Char('Model Name', required=True)

    # relations
    brand_id = fields.Many2one('customer.vehicle.brand', "Brand", required=True)

    _sql_constraints = [
        ('code_model_name', 'unique (model_name)', 'The model name must be unique per record !'),
    ]


class CustomerVehicle(models.Model):
    _name = 'customer.vehicle'
    _description = 'Customer Vehicle'
    _rec_name = 'license_number'

    # attributes
    license_number = fields.Char('Licence Plate Number')

    # relations
    model_id = fields.Many2one('customer.vehicle.model', 'Model')
    brand_id = fields.Many2one('customer.vehicle.brand', 'Brand')
    fuel_type_id = fields.Many2one('fuel.type', 'Fuel Type')
    year = fields.Char('Year')

    def vehicle_service_order(self):
        return {
            'name': ('Repair Order'),
            'view_mode': 'tree,form',
            'res_model': 'repair.order',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('vehicle_id', '=', self.id), ('repair_type', '=', 'service')]
        }

    def vehicle_quotation(self):
        return {
            'name': ('Quotation'),
            'view_mode': 'tree,form',
            'res_model': 'repair.order',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('vehicle_id', '=', self.id), ('repair_type', '=', 'quote')],
        }