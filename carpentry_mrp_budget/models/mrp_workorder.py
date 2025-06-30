# -*- coding: utf-8 -*-

from odoo import models, fields

class ManufacturingOrder(models.Model):
    _inherit = ['mrp.workorder']

    costs_hour_account_id = fields.Many2one(
        related='workcenter_id.costs_hour_account_id',
    )

    def _get_budget_date_field(self):
        """ Date of budget report """
        return 'date_planned_start'
