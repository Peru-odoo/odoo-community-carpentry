# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from collections import defaultdict

class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['purchase.order', 'carpentry.budget.reservation.mixin']

    #====== Fields ======#
    affectation_ids = fields.One2many(domain=[('section_res_model', '=', _name)])
    budget_analytic_ids = fields.Many2many(
        inverse='_inverse_budget_analytic_ids',
    )

    #====== Affectation refresh ======#
    def _get_budget_types(self):
        return ['goods', 'project_global_cost']
    
    def _get_fields_affectation_refresh(self):
        return super()._get_fields_affectation_refresh() + ['order_line']
    
    @api.depends('order_line', 'order_line.analytic_distribution')
    def _compute_budget_analytic_ids(self):
        """ Compute budget analytics shortcuts
            (!) ignores lines of storable products

            Also called from `_compute_amount_budgetable()` when cost of non-stored products changes
        """
        to_compute = self.filtered('project_id')
        if to_compute:
            mapped_analytics = self._get_mapped_project_analytics()

            for purchase in to_compute:
                lines = purchase.order_line.filtered(lambda x: x.product_id.type != 'product')
                purchase.budget_analytic_ids = list(
                    set(lines.analytic_ids._origin.filtered('is_project_budget').ids) &
                    set(mapped_analytics.get(purchase.project_id.id, []))
                )

        return super()._compute_budget_analytic_ids()
    
    def _inverse_budget_analytic_ids(self):
        """ Manual budget choice => update line's analytic distribution """
        for order in self:
            replaced_ids = order.order_line.analytic_ids._origin.filtered('is_project_budget')
            project_budgets = order.project_id._origin.budget_line_ids.analytic_account_id
            new_budgets = order.budget_analytic_ids & project_budgets # in the PO lines and the project

            nb_budgets = len(new_budgets)
            new_distrib = {x.id: 100/nb_budgets for x in new_budgets}
            
            order.order_line._replace_analytic(replaced_ids.ids, new_distrib, 'budget')
    
    def _get_total_by_analytic(self):
        """ Group-sum `price_subtotal` of purchase order_line by analytic account,
             for analytic accounts available in PO's project
             (!) ignores lines of storable products
            :return: Dict like {analytic_id: charged amount}
        """
        self.ensure_one()
        mapped_analytics = self._get_mapped_project_analytics()
        mapped_price = defaultdict(float)
        
        lines = self.order_line.filtered(lambda x: x.product_id.type != 'product')
        for line in lines:
            if not line.analytic_distribution:
                continue

            for analytic_id, percentage in line.analytic_distribution.items():
                analytic_id = int(analytic_id)
                # Ignore cost if analytic not in project's budget
                if analytic_id in mapped_analytics.get(line.project_id.id, []):
                    amount = line.price_subtotal * percentage / 100
                    mapped_price[analytic_id] += amount
        return mapped_price

    #====== Compute amount ======#
    @api.depends('order_line.price_total', 'order_line.product_id')
    def _compute_amount_budgetable(self):
        """ Inspired from native code (purchase/purchase.py/_amount_all)"""
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type and x.product_id.type != 'product')

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))

            order.amount_budgetable = amount_untaxed

            # update automatic budget reservation
            if order.amount_budgetable != order._origin.amount_budgetable:
                order._compute_budget_analytic_ids()

    @api.depends('order_line.price_total', 'order_line.product_id')
    def _compute_amount_gain(self):
        return super()._compute_amount_gain()
