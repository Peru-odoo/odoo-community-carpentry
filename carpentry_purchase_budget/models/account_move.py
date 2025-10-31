# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = ['account.move']

    date_budget = fields.Date(
        related='invoice_date',
        string='Budget date',
        store=True,
    )

    #====== Analytic mixin ======#
    @api.onchange('project_id')
    def _cascade_project_to_line_analytic_distrib(self, new_project_id=None):
        return super()._cascade_project_to_line_analytic_distrib(new_project_id)

# -- break inheritance --
class AccountPayment(models.Model):
    _inherit = ['account.payment']

    date_budget = fields.Date(store=False)

class AccountBankStatementLine(models.Model):
    _inherit = ['account.bank.statement.line']

    date_budget = fields.Date(store=False)
