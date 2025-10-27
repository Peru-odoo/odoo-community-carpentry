# -*- coding: utf-8 -*-

from odoo import models, api, fields

class SaleOrderLine(models.Model):
    _inherit = ['sale.order.line']

    budget_updated = fields.Boolean(
        string='Budget?',
        default=False,
        help="Has project's budget been updated?",
    )

    #==== Analytic mixin (project) ====#
    def _compute_analytic_distribution(self):
        res = super()._compute_analytic_distribution()
        self._compute_analytic_distribution_carpentry()
        return res
