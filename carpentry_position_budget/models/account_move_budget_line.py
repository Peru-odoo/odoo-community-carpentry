# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class AccountMoveBudgetLine(models.Model):
    _inherit = ["account.move.budget.line"]

    is_computed_carpentry = fields.Boolean(
        default=False,
        # A project's line of `account.move.budget.line` is either:
        # - a computed line of budget (`service_prod`, `service_install`, `goods`):
        #   > existance managed in `project_project._compute_position_budget_ids()`
        #   > groupping project's budget by `analytic_account_id`
        #   => all fields are `readonly`
        # - a manual line:
        #   > added by default from budget's template (`service_office`, `consu_project_global`) 
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
        'qty_debit',
        'budget_id', 'budget_id.date_from', 'budget_id.date_to',
        'product_tmpl_id', 'product_tmpl_id.standard_price',
        'product_variant_ids', 'product_variant_ids.standard_price',  'product_variant_ids.date_from',
    )
    def _compute_debit_carpentry(self):
        """ When position's budgets are updated (import or manually),
            update amount(*) in `account.move.budget.line` accordingly
            (*) is `qty_debit` or `debit` depending on product's type (service or goods)
        """
        line_ids_computed = self.filtered('is_computed_carpentry')
        # compute `debit` standardly, since we overriden the field's `compute` arg
        (self - line_ids_computed)._compute_debit_credit()
        if not line_ids_computed.ids: # perf early quit
            return
        
        rg_result = self.env['carpentry.position.budget'].read_group(
            domain=[('project_id', 'in', line_ids_computed.ids)],
            groupby=['project_id', 'analytic_account_id'],
            fields=['amount:sum']
        )
        mapped_data = {
            (x['project_id'][0], x['analytic_account_id'][0]): x['amount']
            for x in rg_result
        }

        for line in line_ids_computed:
            key = (line.project_id.id, line.analytic_account_id.id)
            field = 'debit' if line.type == 'standard' else 'qty_debit'
            line[field] = mapped_data.get(key)


    #===== Button ======#
    def button_open_budget_line_form(self):
        return super().button_open_budget_line_form() | (
            {'view_id': 'carpentry_position_budget.view_account_move_budget_line_form_readonly'}
            if self.is_computed_carpentry else {}
        )
