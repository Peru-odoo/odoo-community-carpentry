# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions

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
    date = fields.Date(
        compute='_compute_date',
        store=True,
        readonly=False,
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

    #===== Constrain =====#
    @api.ondelete(at_uninstall=False)
    def _unlink_except_not_computed_carpentry(self):
        if self._context.get('unlink_line_no_raise'):
            return
        
        if self.filtered(lambda x: x.is_computed_carpentry):
            raise exceptions.ValidationError(
                _('Budget lines computed from Positions cannot be removed (%s)')
                % self.analytic_account_id.mapped('display_name')
            )

    #===== Compute =====#
    @api.depends('budget_id.date_from')
    def _compute_date(self):
        """ Update computed line's `date` on budget's date """
        line_ids_computed = self.filtered('is_computed_carpentry')
        for line in line_ids_computed:
            line.date = line.budget_id.date_from
    
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

        # compute `debit` standardly, since we override the field's `compute` arg
        super(AccountMoveBudgetLine, self - line_ids_computed)._compute_debit_credit()

        # perf early quit
        if not line_ids_computed:
            return
        
        # Get budget project's groupped by analytic account
        rg_result = self.env['carpentry.budget.available']._read_group(
            domain=[('project_id', 'in', self.project_id._origin.ids), ('group_res_model', '=', 'carpentry.position')],
            groupby=['project_id', 'analytic_account_id'],
            fields=['subtotal:sum'],
            lazy=False,
        )
        budget_brut = {
            (x['project_id'][0], x['analytic_account_id'][0]): x['subtotal']
            for x in rg_result
        }

        # Write in budget lines
        for line in line_ids_computed:
            key = (line.project_id._origin.id, line.analytic_account_id._origin.id)
            field = 'debit' if line.type == 'amount' else 'qty_debit'
            line[field] = budget_brut.get(key, 0.0)
