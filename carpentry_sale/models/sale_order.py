# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command, _

class SaleOrder(models.Model):
    _inherit = ['sale.order']

    #===== Fields =====#
    # new fields
    description = fields.Char(
        string='Name'
    )
    comment = fields.Text(string='Internal Note')
    lines_validated = fields.Selection(
        selection=[
            ('none', 'None'),
            ('not_validated', 'Partial'),
            ('all_validated', 'OK')    
        ],
        string='Line state',
        compute='_compute_lines_validated',
        search='_search_lines_validated',
        default=False,
    )

    # totals
    amount_untaxed_validated = fields.Monetary(
        string="Untaxed Amount (validated lines)",
        store=True,
        compute='_compute_totals_validated',
        tracking=7
    )
    amount_tax_validated = fields.Monetary(
        string="Taxes (validated lines)", 
        store=True,
        compute='_compute_totals_validated'
    )
    amount_total_validated = fields.Monetary(
        string="Total (validated lines)",
        store=True,
        compute='_compute_totals_validated',
        tracking=6
    )

    #===== Compute ======#
    @api.depends('name', 'description')
    def _compute_display_name(self):
        """ Prefix SO's `display_name` with project's """
        for order in self:
            order.display_name = f"[{order.name}] {order.project_id.name} - {order.description or ''}"


    #====== Compute: line status =====#
    @api.depends('order_line', 'order_line.validated')
    def _compute_lines_validated(self):
        for order in self:
            if not order.order_line.ids:
                order.lines_validated = 'none'
            elif set(order.order_line.mapped('validated')) == {True}:
                order.lines_validated = 'all_validated'
            else:
                order.lines_validated = 'not_validated'
    
    @api.model
    def _search_lines_validated(self, operator, value):
        if value == 'none':
            return [('order_line', '=', False)]
        elif value == 'all_validated':
            return [('order_line.validated', '=', True)]
        elif value == 'not_validated':
            return [('order_line.validated', '=', False)]

    def action_confirm(self):
        """ When a user validates a quotation, validate all lines """
        self.order_line.validated = True
        return super().action_confirm

    #====== Compute: totals (validated / not validated) =====#
    @api.depends('amount_total', 'order_line', 'order_line.validated')
    def _compute_totals_validated(self):
        """ Compute the total amounts of the SO **only for the validated lines** """
        for order in self:
            order._compute_totals_validated_one()
    
    def _compute_totals_validated_one(self):
        self.ensure_one()
        order_lines = self.order_line.filtered(lambda x: not x.display_type and x.validated)

        if self.company_id.tax_calculation_rounding_method == 'round_globally':
            tax_results = self.env['account.tax']._compute_taxes([
                line._convert_to_tax_base_line_dict()
                for line in order_lines
            ])
            totals = tax_results['totals']
            amount_untaxed_validated = totals.get(self.currency_id, {}).get('amount_untaxed', 0.0)
            amount_tax_validated = totals.get(self.currency_id, {}).get('amount_tax', 0.0)
        else:
            amount_untaxed_validated = sum(order_lines.mapped('price_subtotal'))
            amount_tax_validated = sum(order_lines.mapped('price_tax'))

        self.amount_untaxed_validated = amount_untaxed_validated
        self.amount_tax_validated = amount_tax_validated
        self.amount_total_validated = amount_untaxed_validated + amount_tax_validated
