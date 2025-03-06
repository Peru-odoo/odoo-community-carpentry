# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from collections import defaultdict
from odoo.tools import float_compare

class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['purchase.order', 'carpentry.budget.reservation.mixin']

    #====== Fields ======#
    affectation_ids = fields.One2many(domain=[('section_res_model', '=', _name)])
    warning_budget = fields.Boolean(compute='_compute_warning_budget')
    amount_budgetable = fields.Monetary(
        string='Budgetable Amount',
        readonly=True,
        compute='_compute_amount_budgetable'
    )

    #====== Affectation refresh ======#
    @api.depends('order_line', 'order_line.analytic_distribution')
    def _compute_affectation_ids(self):
        self.readonly_affectation = True # tells the user to Save
        return super()._compute_affectation_ids()
    
    @api.depends('order_line', 'order_line.analytic_distribution')
    def _compute_budget_analytic_ids(self):
        """ Compute budget analytics shortcuts
            (!) ignores lines of storable products
        """
        for purchase in self:
            project_budgets = purchase.project_id.budget_line_ids.analytic_account_id
            lines = purchase.order_line.filtered(lambda x: x.product_id.type != 'product')
            purchase.budget_analytic_ids = lines.analytic_ids.filtered('is_project_budget') & project_budgets

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

    #====== Compute ======#
    @api.depends('amount_untaxed', 'affectation_ids')
    def _compute_warning_budget(self):
        prec = self.env['decimal.precision'].precision_get('Product Price')
        states = ['to approve', 'approved', 'purchase', 'done']
        for purchase in self:
            compare = float_compare(purchase.amount_budgetable, purchase.sum_quantity_affected, precision_digits=prec)
            purchase.warning_budget = purchase.state in states and compare != 0

    @api.depends('order_line.price_total', 'order_line.product_id.type')
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
