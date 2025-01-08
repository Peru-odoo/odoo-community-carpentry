# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class AccountMoveBudgetLine(models.Model):
    _inherit = ["account.move.budget.line"]

    is_computed_carpentry = fields.Boolean(
        default=False,
        # A project's line of `account.move.budget.line` is either:
        # - a computed line of budget (`production`, `installation`, `goods`):
        #   > existance managed in `project_project._compute_position_budget_ids()`
        #   > groupping project's budget by `analytic_account_id`
        #   => all fields are `readonly`
        # - a manual line:
        #   > added by default from budget's template (`service`, `consu_project_global`) 
        #   > added by user (only for `consu_project_global`')
        #   => fields are writable (especially `qty_debit`)
    )
    debit = fields.Monetary(
        compute='_compute_debit_carpentry',
        store=True,
        readonly=False
    )
    qty_debit = fields.Float(
        compute='_compute_debit_carpentry',
        store=True,
        readonly=False
    )

    @api.depends(
        # 1. positions' budgets
        'project_id.position_budget_ids',
        'project_id.position_budget_ids.amount',
        # 2. positions quantity
        'project_id.position_ids',
        'project_id.position_ids.quantity',
        # standard `@api.depends` for `debit`
        'qty_debit', 'standard_price',
        # 1b. valuations of qties -> budget's dates
        'budget_id', 'budget_id.date_from', 'budget_id.date_to',
        # 1a. price per dates table
        'analytic_account_id',
        'timesheet_cost_history_ids',
        'timesheet_cost_history_ids.hourly_cost',
        'timesheet_cost_history_ids.starting_date'
    )
    def _compute_debit_carpentry(self):
        """ When position's budgets are updated (import or manually),
            update amount(*) in `account.move.budget.line` accordingly
            (*) is `qty_debit` or `debit` depending on product's type (service or goods)
        """
        line_ids_computed = self.filtered('is_computed_carpentry')

        # compute `debit` standardly, since we overriden the field's `compute` arg
        super(AccountMoveBudgetLine, self - line_ids_computed)._compute_debit_credit()

        # perf early quit
        if not line_ids_computed.ids:
            return
        
        # Get budget project's groupped by analytic account
        budget_brut, _ = self.project_id.position_budget_ids.sum(
            quantities=self.project_id._get_quantities(),
            groupby_budget='analytic_account_id',
            groupby_group=['group_id']
        )

        # Write in budget lines
        for line in line_ids_computed:
            amount = budget_brut.get(line.project_id.id, {}).get(line.analytic_account_id.id, 0.0)
            field = 'debit' if line.type == 'amount' else 'qty_debit'
            line[field] = amount
