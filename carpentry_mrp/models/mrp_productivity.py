# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class MrpProductivity(models.Model):
    _inherit = ['mrp.workcenter.productivity']

    @api.depends('duration_hours')
    def _compute_performance(self):
        """ Just add @api.depends """
        super()._compute_performance()
