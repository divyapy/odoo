# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AssignMechanicWizard(models.TransientModel):
    _name = 'assign.mechanic.wizard'
    _description = 'Assign Mechanic Wizard'

    # relations
    mechanic_ids = fields.Many2many('hr.employee', string="Assign Mechanic")
    repair_id = fields.Many2one("repair.order")

    def assign_mechanic(self):
        """
        Assign mechanic to the repair.order.
        """
        self.repair_id.mechanic_ids = [(6, 0, self.mechanic_ids.ids)]
        return True

class AssignBayWizard(models.TransientModel):
    _name='assign.bay.wizard'
    _description = 'Assign Bay Wizard'

    # relations
    bay_id = fields.Many2one("bay", "Bay")
    repair_id = fields.Many2one("repair.order")

    def assign_bay(self):
        """
        Assign bay to the repair.order.
        """
        self.repair_id.assign_bay_id = self.bay_id
        return True