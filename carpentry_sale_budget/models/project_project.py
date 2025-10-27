# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from collections import defaultdict

class Project(models.Model):
    _inherit = ['project.project']

    #---- fees ----
    fees_prorata = fields.Monetary(
        string='Prorata',
        compute='_compute_budget_fees_and_margins',
    )
    fees_structure = fields.Monetary(
        string='Structure',
        compute='_compute_budget_fees_and_margins',
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
    #---- initial margins: [Market - Budget] ----
    margin_contributive = fields.Monetary(
        string='Contributive margin',
        compute='_compute_budget_fees_and_margins',
        help='Total market - All budgets - Only prorata fees (i.e. not structure fees)'
    )
    margin_costs = fields.Monetary(
        string='Margin on costs',
        compute='_compute_budget_fees_and_margins',
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
    #---- actual margins: [Reserved Budget - Real Expense] ----
    margin_contributive_actual = fields.Monetary(
        string='Contributive margin (actual)',
        compute='_compute_budget_fees_and_margins',
        help='[Reserved Budget] - [Real Expense] - [Only prorata fees (i.e. not structure fees)]'
    )
    margin_costs_actual = fields.Monetary(
        string='Margin on costs (actual)',
        compute='_compute_budget_fees_and_margins',
        help='[Reserved Budget] - [Real Expense] - [All fees]',
    )
    # actuel margins' rates
    margin_contributive_actual_rate = fields.Integer(
        string='Contributive margin (actual) (%)',
        compute='_compute_budget_fees_and_margins'
    )
    margin_costs_actual_rate = fields.Integer(
        string='Margin on costs (actual) (%)',
        compute='_compute_budget_fees_and_margins',
    )
    budget_reservation_progress = fields.Integer(
        string='Budget reservation progress (%)',
        compute='_compute_budget_fees_and_margins',
    )

    # sale order line updated status (for warning)
    budget_up_to_date = fields.Boolean(
        compute='_compute_budget_up_to_date',
        help='Reliability score of actuals indicator, computed as [Reserved budget / Available budget]',
    )

    #===== Compute: fees, margins =====#
    @api.depends('fees_prorata_rate', 'fees_structure_rate', 'market_reviewed', 'budget_line_sum')
    def _compute_budget_fees_and_margins(self):
        # 2. Reserved budget & real expense
        rg_expense = self.env['carpentry.budget.expense']._read_group(
            domain=[('project_id', 'in', self.ids)],
            fields=['amount_reserved_valued:sum', 'amount_expense_valued:sum'],
            groupby=['project_id'],
        )
        mapped_expense = {
            x['project_id'][0]: {'reserved': x['amount_reserved_valued'], 'expense': x['amount_expense_valued']}
            for x in rg_expense
        }
        
        for project in self:
            project._compute_budget_fees_and_margins_one(mapped_expense)
        
    def _compute_budget_fees_and_margins_one(self, mapped_expense):
        # fees
        self.fees_prorata   = self.fees_prorata_rate * self.market_reviewed / 100
        self.fees_structure = self.fees_structure_rate * self.market_reviewed / 100

        # initial margins
        self.margin_costs        = self.market_reviewed - self.budget_line_sum - self.fees_prorata - self.fees_structure
        self.margin_contributive = self.market_reviewed - self.budget_line_sum - self.fees_prorata # ie. on direct costs only
        # actual margins
        x = mapped_expense.get(self._origin.id, {'reserved': 0.0, 'expense': 0.0})
        self.margin_costs_actual           = x['reserved'] - x['expense'] - self.fees_prorata - self.fees_structure
        self.margin_contributive_actual    = x['reserved'] - x['expense'] - self.fees_prorata

        # rates
        if self.market_reviewed:
            # initial margins
            self.margin_costs_rate        = self.margin_costs / self.market_reviewed * 100
            self.margin_contributive_rate = self.margin_contributive / self.market_reviewed * 100
            # actual margins
            self.margin_costs_actual_rate        = self.margin_costs_actual / self.market_reviewed * 100
            self.margin_contributive_actual_rate = self.margin_contributive_actual / self.market_reviewed * 100
        else:
            # initial margins
            self.margin_costs_rate        = 0.0
            self.margin_contributive_rate = 0.0
            # actual margins
            self.margin_costs_actual_rate        = 0.0
            self.margin_contributive_actual_rate = 0.0
        
        self.budget_reservation_progress = bool(self.budget_line_sum) and x['reserved'] / self.budget_line_sum * 100

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
