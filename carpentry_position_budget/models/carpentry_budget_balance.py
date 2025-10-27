# -*- coding: utf-8 -*-

from re import A
from odoo import models, fields, api, Command, exceptions, _

class CarpentryBudgetBalance(models.Model):
    """ This model acts as a real `section` (models.Models), like PO, MO, ...
        to adjust budget and make balances
    """
    _name = "carpentry.budget.balance"
    _inherit = ['project.default.mixin', 'carpentry.budget.mixin']
    _description = "Budget Balance"
    _carpentry_budget_alert_banner_xpath = False # don't use budget view templates
    _carpentry_budget_smartbuttons_xpath = False
    _carpentry_budget_notebook_page_xpath = False

    #===== Fields =====#
    name = fields.Char()
    project_id = fields.Many2one(readonly=True)
    reservation_ids = fields.One2many(domain=[('section_res_model', '=', _name)])
    launch_ids = fields.Many2many(
        string='Launchs',
        comodel_name='carpentry.group.launch',
        compute='_compute_launch_ids',
        readonly=False,
        domain="[('project_id', '=', project_id)]",
    )

    #===== Budget reservation methods =====#
    def _depends_can_reserve_budget(self):
        return []
    def _get_domain_can_reserve_budget(self):
        return []
    
    def _get_budget_types(self):
        return [x[0] for x in self.env['account.analytic.account']._fields['budget_type'].selection]
    
    def _get_domain_is_temporary_gain(self):
        return []
    
    @api.depends('reservation_ids.launch_id')
    def _compute_launch_ids(self):
        """ `launch_ids` are not stored. They are:
            * selected by user
            * computed back from reservations
        """
        for balance in self:
            balance.launch_ids = balance.reservation_ids.launch_id
    
    def _get_launch_ids(self):
        """ For balance: either launchs, either project """
        return self.launch_ids.ids or [False]
    
    @api.depends('project_id', 'launch_ids')
    def _compute_budget_analytic_ids(self):
        return super()._compute_budget_analytic_ids()
    def _get_auto_budget_analytic_ids(self):
        """ Budget centers are either all launch's or project's:
             a) all project's global budgets, if no launch selected
             b) all launch's budgets, if at least 1 `launch_ids` is selected
            Thus: budget balance are either for project's or launchs' budgets.
        """
        if self.launch_ids:
            # Select budgets related to the launchs
            position_ids = self.launch_ids.affectation_ids.position_id
            rg_result = self.env['carpentry.position.budget'].read_group(
                domain=[('position_id', 'in', position_ids.ids)],
                groupby=['project_id'],
                fields=['analytic_account_id:array_agg'],
            )
            mapped_data = {
                x['project_id'][0]: x['analytic_account_id']
                for x in rg_result
            }
        else:
            # Select project's budgets
            domain = [('is_computed_carpentry', '=', False)]
            mapped_data = self._get_mapped_project_analytics(domain)

        return mapped_data.get(self.project_id.id, [])

    def _get_total_budgetable_by_analytic(self):
        """ [OVERRIDE]
            Balance => budget to reserve is *all* remaining budget (instead of expense)
        """
        self.ensure_one()
        remaining_budget = self.budget_analytic_ids._get_remaining_budget_by_analytic(
            launchs=self.launch_ids, sections=self
        )
        return {
            (self.project_id.id, aac_id): amount_subtotal
            for aac_id, amount_subtotal in remaining_budget.items() 
        }
