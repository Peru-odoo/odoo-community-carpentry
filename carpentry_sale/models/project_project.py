# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import float_compare

class ProjectProject(models.Model):
    _inherit = "project.project"

    # market
    market = fields.Monetary(
        string='Market',
        help='Amount of initial contract with the customer.'
    )
    market_reviewed = fields.Monetary(
        string='Reviewed Market',
        compute='_compute_market_reviewed',
        help='Initial market + validated sale order lines (based on analytic distribution)'
    )

    # sale order
    sale_order_sum_validated = fields.Monetary(
        string='Quotations & Sale Orders total validated amount',
        compute='_compute_sale_order_fields',
        store=True
    )
    sale_order_lines_fully_validated = fields.Boolean(
        compute='_compute_sale_order_lines_fully_validated',
    )


    #===== Compute: Market =====
    @api.onchange('opportunity_id')
    def _onchange_opportunity_id(self):
        """ Pre-fill `Market` with opportunity's `Expected revenue` """
        for project in self:
            project.market = project.opportunity_id.expected_revenue

    @api.depends('market', 'sale_order_sum_validated')
    def _compute_market_reviewed(self):
        for project in self:
            project.market_reviewed = project.market + project.sale_order_sum_validated


    #===== Compute: Sale Order lines =====#
    @api.depends('sale_order_ids', 'sale_order_ids.amount_untaxed', 'sale_order_ids.amount_untaxed_validated')
    def _compute_sale_order_fields(self):
        """ Just overwritte the @api.depends() """
        return super()._compute_sale_order_fields()

    def _get_rg_sale_order_fields(self):
        """ See `sale_project_link` """
        return super()._get_rg_sale_order_fields() | {
            ('sale_order_sum_validated', 'amount_untaxed_validated:sum', 'amount_untaxed_validated')
        }

    @api.depends('sale_order_sum_validated', 'sale_order_sum')
    def _compute_sale_order_lines_fully_validated(self):
        for project in self:
            project.sale_order_lines_fully_validated = bool(0 == float_compare(
                project.sale_order_sum_validated,
                project.sale_order_sum,
                precision_rounding=project.currency_id.rounding
            ))
