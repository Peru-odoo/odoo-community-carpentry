# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from collections import defaultdict
from odoo.tools import float_round

class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['purchase.order', 'carpentry.budget.reservation.mixin']

    #====== Fields ======#
    affectation_ids = fields.One2many(domain=[('section_res_model', '=', _name)])

    #====== Affectation refresh ======#
    @api.depends('order_line', 'order_line.analytic_distribution')
    def _compute_affectation_ids(self):
        """ Inherite to add fields in @api.depends """
        return super()._compute_affectation_ids()
    
    @api.depends('order_line', 'order_line.analytic_distribution')
    def _compute_budget_analytic_ids(self):
        """ Compute budget analytics shortcuts
            (!) ignores lines of storable products

            Also called from `_compute_amount_budgetable()` when cost of non-stored products changes
        """
        for purchase in self:
            project_budgets = purchase.project_id._origin.budget_line_ids.analytic_account_id
            lines = purchase.order_line.filtered(lambda x: x.product_id.type != 'product')
            purchase.budget_analytic_ids = lines.analytic_ids._origin.filtered('is_project_budget') & project_budgets

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
