# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryBudgetRemaining(models.Model):
    _inherit = ['carpentry.budget.remaining']

    #===== Fields =====#
    task_id = fields.Many2one(
        comodel_name='project.task',
        string='Task',
        readonly=True,
    )
