# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountAnalyticAccount(models.Model):
    _inherit = ['account.analytic.account']

    budget_only_accountant = fields.Boolean(
        string='Only selectable by accountant?',
        default=False,
        help='Only relevant for selection in budgets. If checked, the analytic'
             ' account will only be choosable by accountants in budget lines, and project'
             ' managers won`t be able to manually add it to their projects.',
    )
