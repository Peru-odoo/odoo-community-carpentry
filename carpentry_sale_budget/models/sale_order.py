# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command, _

class SaleOrder(models.Model):
    _inherit = ['sale.order']

    lines_budget_updated = fields.Selection(
        selection=[
            ('none', 'None'),
            ('not_updated', 'Partial'),
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
            if not order.order_line.ids:
                order.lines_budget_updated = 'none'
            elif set(order.order_line.mapped('budget_updated')) == {True}:
                order.lines_budget_updated = 'all_updated'
            else:
                order.lines_budget_updated = 'not_updated'
    
    def _search_lines_budget_updated(self, operator, value):
        if value == 'none':
            return [('order_line', '=', False)]
        elif value == 'all_updated':
            return [('order_line.budget_updated', '=', True)]
        elif value == 'not_updated':
            return [('order_line.budget_updated', '=', False)]
