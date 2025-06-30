# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = ['account.move']

    def _get_budget_date_field(self):
        return 'invoice_date'
