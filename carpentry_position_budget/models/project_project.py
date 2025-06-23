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

    # project's budget totals (from budget mixin) => store because project form is often displayed
    budget_prod = fields.Float(store=True)
    budget_install = fields.Float(store=True)
    budget_office = fields.Float(store=True)
    budget_goods = fields.Float(store=True, readonly=True)
    budget_global_cost = fields.Float(store=True, readonly=True)
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
    def _compute_budget_fields(self):
        """ Replace `affectation_ids` by `affectation_ids_project` """
        return [
            field for field in super()._compute_budget_fields()
            if not field.startswith('affectation_ids')
        ] + [
            'affectation_ids_project', 'affectation_ids_project.quantity_affected'
        ]

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
        # Compute project-level budgets from budget line
        budget_fields = {
            # field, (budget_type, budget_field)
            'budget_office': ('service', 'qty_debit'),
            'budget_prod': ('production', 'qty_debit'),
            'budget_install': ('installation', 'qty_debit'),
            'budget_goods': ('goods', 'balance'),
            'budget_global_cost': ('project_global_cost', 'balance')
        }
        for project in self:
            # Ensure budget lines are up-to-date before updating project's totals
            project.sudo()._populate_account_move_budget_line()
            project.sudo().budget_line_ids._compute_debit_carpentry()
            project.sudo().budget_line_ids._compute_debit_credit()

            # from module `project_budget`
            project.budget_total = project.budget_line_sum

            for field, (budget_type, budget_field) in budget_fields.items():
                lines = project.budget_line_ids.filtered(lambda x: x.budget_type == budget_type)
                project[field] = sum(lines.mapped(budget_field))

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
        existing_line_ids = self.budget_line_ids.filtered('is_computed_carpentry')._origin
        analytic_account_ids = self.position_budget_ids.mapped('analytic_account_id')._origin

        to_add = analytic_account_ids - existing_line_ids.analytic_account_id
        to_remove = existing_line_ids.analytic_account_id - analytic_account_ids

        # Delete lines without budget anymore from positions
        domain_unlink = [('analytic_account_id', 'in', to_remove.ids)]
        lines_unlink = self.budget_line_ids.filtered_domain(domain_unlink)
        lines_unlink.sudo().with_context(unlink_line_no_raise=True).unlink()

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
