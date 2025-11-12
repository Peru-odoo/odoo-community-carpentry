# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryBudgetReservation(models.Model):
    _inherit = ["carpentry.budget.reservation"]

    task_id = fields.Many2one(
        comodel_name='project.task',
        string='Task',
        ondelete='cascade',
    )

    def _get_record_fields(self):
        return super()._get_record_fields() + ['task_id']
