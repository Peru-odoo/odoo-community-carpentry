# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

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
            ('partial_validated', 'Partial'),
            ('all_validated', 'OK')    
        ],
        string='Line state',
        compute='_compute_lines_validated',
        search='_search_lines_validated',
        default=False,
    )

    # totals
    amount_untaxed = fields.Monetary(help="Validated")
    amount_tax = fields.Monetary(help="Validated")
    amount_total = fields.Monetary(help="Validated")

    amount_untaxed_to_validate = fields.Monetary(
        string="Untaxed amount (to validate)",
        store=True,
        compute='_compute_amounts',
    )
    amount_total_to_validate = fields.Monetary(
        string="To validate",
        help="Total be to validated",
        store=True,
        compute='_compute_amounts',
    )
    tax_totals_to_validate = fields.Binary(compute='_compute_tax_totals', exportable=False)

    #===== Compute ======#
    @api.depends('name', 'description')
    def _compute_display_name(self):
        """ Prefix SO's `display_name` with project's """
        for order in self:
            dash = ' - ' if order.project_id.name else ''
            description = (order.project_id.name or '') + dash + (order.description or '')
            order.display_name = f'[{order.name}] {description}' if description else order.name

    #====== Compute: line status =====#
    @api.depends('order_line', 'order_line.validated')
    def _compute_lines_validated(self):
        for order in self:
            so_line = order.order_line.filtered(lambda x: not x.display_type)
            validated = set(so_line.mapped('validated'))
            if validated == {True}:
                state = 'all_validated'
            elif validated == {True, False}:
                state = 'partial_validated'
            else:
                state = 'none'
            order.lines_validated = state
    
    @api.model
    def _search_lines_validated(self, operator, value, sol_field='validated'):
        if operator not in ['=', '!=']:
            raise exceptions.UserError(_('Operation not supported'))

        rg_result = self.env['sale.order.line'].read_group(
            domain=[], fields=[], groupby=['order_id', sol_field], lazy=False,
        )
        positive, negative = [], []
        for x in rg_result:
            if x[sol_field]:
                positive.append(x['order_id'][0])
            else:
                negative.append(x['order_id'][0])

        if value == 'none':
            ids = set(negative) - set(positive)
        elif value.startswith('all_'):
            ids = set(positive) - set(negative)
        else: # partial
            ids = set(positive) & set(negative)
        
        operator = 'in' if operator == '=' else 'not in'
        value = list(ids)
        return [('id', operator, value)]

    def action_confirm(self):
        """ When a user validates a quotation, validate all lines """
        self.order_line.validated = True
        return super().action_confirm()

    #====== Compute: totals (validated / not validated) =====#
    @api.depends('order_line.validated')
    def _compute_amounts(self):
        """ Replaces native total by *validated* totals
            and computes *remaining to validate* thresholds
        """
        for order in self:
            ol_all, ol_validated = order._get_order_line_filtered()

            # replace native totals
            order.amount_untaxed, order.amount_tax = order._get_amounts_totals(ol_validated)
            order.amount_total = order.amount_untaxed + order.amount_tax

            # compute remaining to validate
            if order.state == 'cancel':
                order.amount_untaxed_to_validate = 0.0
                order.amount_total_to_validate = 0.0
            else:
                order.amount_untaxed_to_validate, tax_to_validate = order._get_amounts_totals(ol_all - ol_validated)
                order.amount_total_to_validate = order.amount_untaxed_to_validate + tax_to_validate
    
    def _get_order_line_filtered(self):
        self.ensure_one()
        self = self.with_company(self.company_id)
        ol_all = self.order_line.filtered(lambda x: not x.display_type)
        ol_validated = ol_all.filtered('validated')
        return ol_all, ol_validated
    
    def _get_amounts_totals(self, order_lines):
        """ Calculate and returns *untaxed* subtotal and *tax* amount
            This is a copy/paste of native code

            :order_lines: either *all* or *validated* lines
            :return:      tuple (amount_untaxed, amount_tax) where sum of the 2
                          makes the great total (taxes included)
        """
        self.ensure_one()

        if self.company_id.tax_calculation_rounding_method == 'round_globally':
            tax_results = self.env['account.tax']._compute_taxes([
                line._convert_to_tax_base_line_dict()
                for line in order_lines
            ])
            totals = tax_results['totals']
            amount_untaxed = totals.get(self.currency_id, {}).get('amount_untaxed', 0.0)
            amount_tax = totals.get(self.currency_id, {}).get('amount_tax', 0.0)
        else:
            amount_untaxed = sum(order_lines.mapped('price_subtotal'))
            amount_tax = sum(order_lines.mapped('price_tax'))
        
        return amount_untaxed, amount_tax

    def _compute_tax_totals(self):
        for order in self:
            ol_all, ol_validated = order._get_order_line_filtered()
            order.tax_totals = order._get_tax_totals(ol_validated)
            order.tax_totals_to_validate = order._get_tax_totals(ol_all - ol_validated)
    def _get_tax_totals(self, order_lines):
        self.ensure_one()
        return self.env['account.tax']._prepare_tax_totals(
            [x._convert_to_tax_base_line_dict() for x in order_lines],
            self.currency_id or self.company_id.currency_id,
        )
