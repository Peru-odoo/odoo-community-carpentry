# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import float_compare

class Project(models.Model):
    _inherit = ["project.project"]

    #===== Fields =====
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
    so_lines_validated = fields.Boolean(
        compute='_compute_so_lines_validated',
    )

    #===== Compute: Market =====
    @api.onchange('opportunity_id')
    def _onchange_opportunity_id(self):
        """ Pre-fill `Market` with opportunity's `Expected revenue` """
        for project in self:
            project.market = project.opportunity_id.expected_revenue

    @api.depends('market', 'sale_order_sum')
    def _compute_market_reviewed(self):
        for project in self:
            project.market_reviewed = project.market + project.sale_order_sum


    #===== Compute: Sale Order lines =====#
    @api.depends('sale_order_ids.order_line.validated')
    def _compute_so_lines_validated(self):
        rg_result = self.env['sale.order.line'].read_group(
            domain=[('project_id', 'in', self.ids), ('state', '!=', 'cancel')],
            fields=['validated:array_agg(validated)'],
            groupby=['project_id'],
        )
        mapped_data = {x['project_id'][0]: set(x['validated']) for x in rg_result}
        for project in self:
            project.so_lines_validated = bool(
                mapped_data.get(project.id) == {True}
            )
