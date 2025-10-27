# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['purchase.order', 'carpentry.budget.mixin']
    _carpentry_budget_notebook_page_xpath = '//page[@name="products"]'
    _carpentry_budget_last_valuation_step = _('billing')

    #====== Fields ======#
    reservation_ids = fields.One2many(domain=[('section_res_model', '=', _name)])
    budget_analytic_ids = fields.Many2many(
        relation='carpentry_budget_purchase_analytic_rel',
        column1='order_id',
        column2='analytic_id',
    )

    #====== CRUD ======#
    def write(self, vals):
        res = super().write(vals)
        if 'budget_analytic_ids' in vals:
            self._cascade_order_budgets_to_line_analytic()
        return res
    
    def _cascade_order_budgets_to_line_analytic(self):
        """ Manual budget choice => update line's analytic distribution """
        domain=[('is_project_budget', '=', True)]
        budget_analytics_ids = self.env['account.analytic.account'].search(domain).ids

        for order in self:
            project_budgets = order.project_id.budget_line_ids.analytic_account_id
            new_budgets = order.budget_analytic_ids & project_budgets # in the PO lines and the project

            order.order_line._cascade_order_budgets_to_line_analytic(new_budgets, budget_analytics_ids)

    #====== Budget reservation configuration ======#
    def _get_budget_types(self):
        return ['goods', 'other']
    
    def _get_fields_budget_reservation_refresh(self):
        return super()._get_fields_budget_reservation_refresh() + [
            'order_line', 'order_line.product_id', 'order_line.price_subtotal'
        ]
    
    def _should_value_budget_reservation(self):
        return True
    
    def _depends_can_reserve_budget(self):
        return super()._depends_can_reserve_budget() + ['order_line']
    def _get_domain_can_reserve_budget(self):
        """ Can't reserve budget of all lines are *storable* product """
        return super()._get_domain_can_reserve_budget() + [
            # will be True as soon as 1 line is != product
            ('order_line', '!=', False),
            ('order_line.product_id.type', 'in', ['consu', 'service']),
        ]
    def _get_domain_is_temporary_gain(self):
        return [('invoice_status', '!=', 'invoiced')]
    
    def _should_enforce_internal_analytic(self):
        return hasattr(self, 'product_id') and self.product_id.type == 'product'
    
    #===== Compute: date & amounts =====#
    @api.depends('date_approve')
    def _compute_date_budget(self):
        for order in self:
            order.date_budget = order.date_approve
        return super()._compute_date_budget()
    