# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from collections import defaultdict

class Project(models.Model):
    _inherit = ['project.project']

    # fees
    fees_prorata = fields.Monetary(
        string='Prorata',
        compute='_compute_budget_fees_and_margins',
        currency_field='currency_id'
    )
    fees_structure = fields.Monetary(
        string='Structure',
        compute='_compute_budget_fees_and_margins',
        currency_field='currency_id'
    )
    # fees' rates
    fees_prorata_rate = fields.Float(
        string='Prorata (%)',
        default=0.0,
    )
    fees_structure_rate = fields.Float(
        string='Structure (%)',
        default=0.0,
    )

    # margins
    margin_contributive = fields.Monetary(
        string='Contributive margin',
        compute='_compute_budget_fees_and_margins',
        currency_field='currency_id',
        help='Total market - All budgets - Only prorata fees (i.e. not structure fees)'
    )
    margin_costs = fields.Monetary(
        string='Margin on costs',
        compute='_compute_budget_fees_and_margins',
        currency_field='currency_id',
        help='Total market - All budgets - All fees',
    )
    # margins' rates
    margin_contributive_rate = fields.Integer(
        string='Contributive margin (%)',
        compute='_compute_budget_fees_and_margins'
    )
    margin_costs_rate = fields.Integer(
        string='Margin on costs (%)',
        compute='_compute_budget_fees_and_margins'
    )

    # sale order line updated status (for warning)
    budget_up_to_date = fields.Boolean(
        compute='_compute_budget_up_to_date',
    )

    #===== Compute: fees, margins =====#
    @api.depends('fees_prorata_rate', 'fees_structure_rate', 'market_reviewed', 'budget_line_sum')
    def _compute_budget_fees_and_margins(self):
        for project in self:
            project._compute_budget_fees_and_margins_one()
        
    def _compute_budget_fees_and_margins_one(self):
        # fees
        self.fees_prorata   = self.fees_prorata_rate * self.market_reviewed / 100
        self.fees_structure = self.fees_structure_rate * self.market_reviewed / 100
        # margins
        self.margin_costs        = self.market_reviewed - self.budget_line_sum - self.fees_prorata - self.fees_structure
        self.margin_contributive = self.market_reviewed - self.budget_line_sum - self.fees_prorata # ie. on direct costs only
        # rates
        self.margin_costs_rate        = bool(self.market_reviewed) and self.margin_costs / self.market_reviewed * 100
        self.margin_contributive_rate = bool(self.market_reviewed) and self.margin_contributive / self.market_reviewed * 100

    #===== Compute : sale order line budget updated status =====#
    @api.depends('sale_order_ids.order_line', 'sale_order_ids.order_line.budget_updated', 'sale_order_ids.state')
    def _compute_budget_up_to_date(self):
        domain = [('project_id', 'in', self.ids), ('budget_updated', '=', False), ('state', '!=', 'cancel')]
        partial_updated_project_ids_ = self.env['sale.order.line'].sudo().search(domain).project_id.ids
        
        for project in self:
            project.budget_up_to_date = not (project.id in partial_updated_project_ids_)


    #===== Carpentry Planning =====#
    def get_planning_dashboard_data(self):
        return super().get_planning_dashboard_data() | self._get_planning_dashboard_cost_data()

    def _get_planning_dashboard_cost_data(self):
        return {}
        # {
        #     'market_reviewed': self.market_reviewed,
        #     'budget_line_sum': self.budget_line_sum,
        #     'budget_progress': round(self.budget_progress),
        # }
