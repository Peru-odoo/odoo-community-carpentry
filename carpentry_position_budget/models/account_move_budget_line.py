# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

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
        # 1b. valuations of qties -> budget's dates
        'budget_id', 'budget_id.date_from', 'budget_id.date_to',
        # 1a. products template/variants price & dates
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
            field = 'debit' if line.type == 'standard' else 'qty_debit'
            line[field] = amount
