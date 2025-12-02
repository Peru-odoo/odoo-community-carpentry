# -*- coding: utf-8 -*-

from odoo import api, fields, models

class AccountAnalyticLine(models.Model):
    _inherit = ['account.analytic.line']

    budget_type = fields.Selection(
        related='account_id.budget_type',
        store=True,
        required=False,
        help="Define one to display this expense in project budget reports.",
    )
    budget_project_ids = fields.Many2many(
        string='Budget projects',
        help="Budgets reports of these projects will include this expense.",
        comodel_name='project.project',
        relation='carpentry_budget_analytic_line_project_rel',
        column1='line_id',
        column2='project_id',
    )
    # for SQL view
    move_id = fields.Many2one(
        string='Account Move',
        related='move_line_id.move_id',
        store=True,
    )
    purchase_id = fields.Many2one(
        string='Purchase Order',
        related='move_line_id.purchase_line_id.order_id',
        store=True,
    )
