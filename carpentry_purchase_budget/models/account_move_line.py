# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = ['account.move.line']

    #==== Analytic mixin configuration ====#
    def _compute_analytic_distribution(self):
        res = super()._compute_analytic_distribution()
        self._compute_analytic_distribution_carpentry()
        return res
    
    def _should_enforce_internal_analytic(self):
        return hasattr(self, 'product_id') and self.product_id.type == 'product'
    