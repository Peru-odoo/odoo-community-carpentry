# -*- coding: utf-8 -*-

from odoo import models, api, fields

class SaleOrderLine(models.Model):
    _inherit = ['sale.order.line']

    budget_updated = fields.Boolean(
        string='Budget?',
        default=False,
        help="Has project's budget been updated?",
    )

    #==== project_id cascade & from analytic distribution ====#
    project_id = fields.Many2one(related='')

    def _get_fields_project_id(self):
        return ['order_id']
    
    def _should_enforce_internal_analytic(self):
        """ Forces analytic of *internal* project for all *storable* lines """
        return self.product_id.type == 'product'
    
    def _compute_analytic_distribution(self):
        res = super()._compute_analytic_distribution()
        self._compute_analytic_distribution_carpentry()
        return res
