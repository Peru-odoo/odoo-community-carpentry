# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command, _

class SaleOrder(models.Model):
    _inherit = ['sale.order']

    lines_budget_updated = fields.Selection(
        selection=[
            ('none', 'None'),
            ('partial_updated', 'Partial'),
            ('all_updated', 'OK')
        ],
        string='Budget state',
        compute='_compute_lines_budget_updated',
        search='_search_lines_budget_updated',
        default=False,
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
    
    def _search_lines_budget_updated(self, operator, value):
        if value == 'none':
            return [('order_line.budget_updated', '=', False)]
        elif value == 'all_updated':
            return [('order_line.budget_updated', '=', True)]
        elif value == 'partial_updated':
            return [('order_line.budget_updated', 'not in', [True, False])]
