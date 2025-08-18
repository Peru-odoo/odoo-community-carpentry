# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = ['sale.order']

    lines_budget_updated = fields.Selection(
        selection=[
            ('none', 'None'),
            ('partial_updated', 'Partial'),
            ('all_updated', 'OK'),
        ],
        string='Budget?',
        compute='_compute_lines_budget_updated',
        search='_search_lines_budget_updated',
        default=False,
        help="Has project's budget been updated?",
    )
    
    @api.depends('order_line', 'order_line.budget_updated')
    def _compute_lines_budget_updated(self):
        for order in self:
            updated = set(order.order_line.mapped('budget_updated'))
            if updated == {True}:
                state = 'all_updated'
            elif updated == {True, False}:
                state = 'partial_updated'
            else:
                state = 'none'
            order.lines_budget_updated = state
    
    @api.model
    def _search_lines_budget_updated(self, operator, value):
        """ Same logic than `_search_lines_validated` """
        return self._search_lines_validated(operator, value, sol_field='budget_updated')
