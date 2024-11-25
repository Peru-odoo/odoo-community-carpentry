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
    budget_office = fields.Monetary(
        string='Office',
        compute='_compute_budgets',
        store=True,
        currency_field='currency_id',
    )
    budget_global_fees = fields.Monetary(
        string='Global fees',
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
    def _get_budgets_brut_valued(self):
        """ Override from `carpentry.group.budget.mixin`
            :return: same format than `carpentry_position_budget.sum()`
        """
        brut, valued = {}, {}
        for x in self.budget_line_ids:
            if not x.project_id.id in brut:
                brut[x.project_id.id] = defaultdict(float)
                valued[x.project_id.id] = defaultdict(float)
            brut[x.project_id.id][x.product_tmpl_id.detailed_type] += x.qty_balance
            valued[x.project_id.id][x.product_tmpl_id.detailed_type] += x.balance

        return brut, valued
    
    def _compute_budgets_one(self, brut, valued):
        """ Add fields `budget_office` and `budget_global_fees` """
        super()._compute_budgets_one(brut, valued)
        self.budget_office = self._get_budget_one(brut, 'service_office')
        self.budget_global_fees = self._get_budget_one(valued, ['consu_project_global'])
        self.budget_total = self.budget_line_sum # from module `project_budget`


    @api.depends(
        # 1a. products template/variants price & dates
        'position_budget_ids.analytic_account_id.product_tmpl_id.product_variant_ids',
        'position_budget_ids.analytic_account_id.product_tmpl_id.product_variant_ids.standard_price',
        'position_budget_ids.analytic_account_id.product_tmpl_id.product_variant_ids.date_from',
        # 1b. valuations of qties -> budget's dates
        'budget_ids', 'budget_ids.date_from', 'budget_ids.date_to',
        # 2. positions' budgets
        'position_budget_ids',
        'position_budget_ids.amount',
        # 3. positions quantity
        'position_ids',
        'position_ids.quantity',
        # 4. new or update on fix lines of project's budget (project global fees), in `account.move.budget.line`
        'budget_line_ids',
        'budget_line_ids.qty_balance',
        'budget_line_ids.standard_price',
    )
    def _compute_budgets(self):
        self._populate_account_move_budget_line()
        return super()._compute_budgets()

    #===== Compute/Populate: account_move_budget_line =====#
    def _populate_account_move_budget_line(self):
        """ Create/delete computed lines in `account.move.budget.line` according to
            budgets from positions
        """
        if self._context.get('import_budget_no_compute'):
            return
        
        # Get existing computed lines & list of just-updated 'account_analytic_ids' in position's budgets
        existing_line_ids = self.budget_line_ids.filtered('is_computed_carpentry')
        analytic_account_ids = self.position_budget_ids.mapped('analytic_account_id')

        to_add = analytic_account_ids - existing_line_ids.analytic_account_id
        to_remove = existing_line_ids.analytic_account_id - analytic_account_ids

        # Delete lines without budget anymore from positions
        self.budget_line_ids.filtered_domain([('analytic_account_id', 'in', to_remove.ids)]).unlink()

        # Add new lines, if new budget
        vals_list = [{
            'name': aac_id.product_tmpl_id.name or aac_id.name,
            'date': fields.Date.today(),
            'budget_id': fields.first(self.budget_ids).id,
            'account_id': aac_id.product_tmpl_id._get_product_accounts().get('expense').id,
            'analytic_account_id': aac_id.id,
            'product_tmpl_id': aac_id.product_tmpl_id.id,
            'type': 'date_range' if aac_id.product_tmpl_id.type == 'service' else 'standard',
            'is_computed_carpentry': True,
            'debit': 0, # computed in `account.move.budget.line`
            'qty_debit': 0, # same
        } for aac_id in to_add]
        existing_line_ids.create(vals_list)._compute_debit_carpentry()
    
