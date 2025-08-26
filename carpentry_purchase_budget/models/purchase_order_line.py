# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = ['purchase.order.line']

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

    #==== Budget affectation ====#
    def _inverse_budget_analytic_ids(self, new_budgets, budget_analytics_ids):
        """ Manual budget choice => update line's analytic distribution """
        nb_budgets = len(new_budgets)
        new_distrib = {x: 100/nb_budgets for x in new_budgets.ids}

        self = self.filtered(lambda x: not x._should_enforce_internal_analytic())
        for line in self:
            if not line.analytic_distribution:
                continue
            
            # 1. Clean line's analytic of any other budget
            for k, _ in line.analytic_distribution.items():
                if int(k) in budget_analytics_ids:
                    line.analytic_distribution.pop(k)

            # 2. Set new forced distrib from budgets
            line.analytic_distribution = (line.analytic_distribution or {}) | new_distrib
