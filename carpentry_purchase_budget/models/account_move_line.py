# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = ['account.move.line']

    #==== Analytic mixin configuration ====#
    def _compute_analytic_distribution(self):
        res = super()._compute_analytic_distribution()
        self._compute_analytic_distribution_carpentry()
        return res
    