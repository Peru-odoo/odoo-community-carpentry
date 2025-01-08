# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from collections import defaultdict

class Project(models.Model):
    _name = 'project.project'
    _inherit = ['project.project', 'carpentry.group.budget.mixin']

    position_budget_ids = fields.One2many(
        # required for @depends
        comodel_name='carpentry.position.budget',
        inverse_name='project_id'
    )

    # project's budget totals: mixin + those 2 fields
    budget_office = fields.Float(
        string='Office',
        compute='_compute_budgets',
        store=True,
    )
    budget_global_cost = fields.Monetary(
        string='Global costs',
        compute='_compute_budgets',
        store=True,
        currency_field='currency_id',
    )
    budget_total = fields.Monetary(
        # duplicate with `budget_line_sum` from `project_budget` (already stored) => cancel storage of mixin field `budget_total`
        store=False,
        compute_sudo=True
    )

    # user-interface
    position_warning_name = fields.Boolean(
        related='position_ids.warning_name'
    )

    #===== User interface =====#
    def _get_warning_banner(self):
        """ Show alert banner in project's form in case of a warning on positions' names """
        return super()._get_warning_banner() | self.position_warning_name

    #===== Compute: budget sums =====#
    def _get_quantities(self):
        """ Called from `_get_budgets_brut_valued()` of mixin `carpentry.group.budget.mixin` """
        quantities = {}
        for position in self.position_ids:
            # sum position's affected qty to the group
            key = frozenset({
                'group_id': position.project_id.id,
                'position_id': position.id
            }.items())
            quantities[key] = position.quantity
        
        return quantities

    def _compute_budgets_one(self, brut, valued):
        """ Add fields `budget_office` and `budget_global_cost` """
        super()._compute_budgets_one(brut, valued)

        self.budget_office = self.sudo()._get_budget_one(brut, 'service')
        self.budget_global_cost = self.sudo()._get_budget_one(valued, 'project_global_cost')

        # from module `project_budget`
        self.budget_total = self.budget_line_sum


    @api.depends(
        # 1a. hour valuation per dates
        'budget_line_ids.analytic_account_id',
        'budget_line_ids.analytic_account_id.timesheet_cost_history_ids',
        'budget_line_ids.analytic_account_id.timesheet_cost_history_ids.hourly_cost',
        'budget_line_ids.analytic_account_id.timesheet_cost_history_ids.starting_date',
        # 1b. valuations of qties -> budget's dates
        'budget_ids', 'budget_ids.date_from', 'budget_ids.date_to',
        # 2. positions' budgets
        'position_budget_ids',
        'position_budget_ids.amount',
        # 3. positions quantity
        'position_ids',
        'position_ids.quantity',
        # 4. new or update on fix lines of project's budget (project global costs), in `account.move.budget.line`
        'budget_line_ids',
        'budget_line_ids.qty_balance',
        'budget_line_ids.standard_price',
    )
    def _compute_budgets(self):
        # Ensure budget lines are up-to-date before updating project's totals
        self.sudo()._populate_account_move_budget_line()
        self.sudo().budget_line_ids._compute_debit_carpentry()
        self.sudo().budget_line_ids._compute_debit_credit()

        # Update project's totals
        super()._compute_budgets()

    #===== Compute/Populate: account_move_budget_line =====#
    def _populate_account_move_budget_line(self):
        """ Create/delete computed lines in `account.move.budget.line` according to
            budgets from positions
        """
        if self._context.get('import_budget_no_compute'):
            return
        
        # Ensure project.budget_ids exist, before any further calculations
        self._inverse_budget_template_ids()
        
        # Get existing computed lines & list of just-updated 'account_analytic_ids' in position's budgets
        existing_line_ids = self.budget_line_ids.filtered('is_computed_carpentry')
        analytic_account_ids = self.position_budget_ids.mapped('analytic_account_id')

        to_add = analytic_account_ids - existing_line_ids.analytic_account_id
        to_remove = existing_line_ids.analytic_account_id - analytic_account_ids

        # Delete lines without budget anymore from positions
        domain_unlink = [('analytic_account_id', 'in', to_remove.ids)]
        self.budget_line_ids.filtered_domain(domain_unlink).sudo().unlink()

        # Add new lines, if new budget
        vals_list = [{
            'name': analytic.name,
            'date': self._get_default_project_budget_line_date(self.budget_id),
            'budget_id': self.budget_id.id,
            'analytic_account_id': analytic.id,
            'is_computed_carpentry': True,
            'debit': 0, # computed in `account.move.budget.line`
            'qty_debit': 0, # same
        } for analytic in to_add]
        existing_line_ids.create(vals_list)
