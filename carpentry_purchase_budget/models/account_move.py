# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = ['account.move']

    date_budget = fields.Date(
        related='invoice_date',
        string='Budget date',
        store=True,
    )

# -- break inheritance --
class AccountPayment(models.Model):
    _inherit = ['account.payment']

    date_budget = fields.Date(store=False)

class AccountBankStatementLine(models.Model):
    _inherit = ['account.bank.statement.line']

    date_budget = fields.Date(store=False)
