# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = ['purchase.order.line']

    #==== Analytic mixin configuration ====#
    def _compute_analytic_distribution(self):
        res = super()._compute_analytic_distribution()
        self._compute_analytic_distribution_carpentry()
        return res

    #==== Budget reservation ====#
    def _cascade_order_budgets_to_line_analytic(self, new_budgets, budget_analytics_ids):
        """ Manual budget choice on PO => update line's analytic distribution """
        nb_budgets = len(new_budgets)
        new_distrib = {x: 100/nb_budgets for x in new_budgets.ids}

        self = self.filtered(lambda x: not x._should_enforce_internal_analytic())
        for line in self:
            # 1. Clean line's analytic of any other budget
            distrib = line.analytic_distribution or {}
            if line.analytic_distribution:
                for k, _ in line.analytic_distribution.items(): # don't browse `distrib` since it may change size
                    if int(k) in budget_analytics_ids and k in distrib:
                        del distrib[k]

            # 2. Set new forced distrib from budgets
            line.analytic_distribution = distrib | new_distrib
