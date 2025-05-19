# -*- coding: utf-8 -*-

from re import A
from odoo import models, fields, api, Command, exceptions, _

class CarpentryBudgetBalance(models.Model):
    """ This model acts as a real `section` (models.Models), like PO, MO, ...
        to adjust budget and make balances
    """
    _name = "carpentry.budget.balance"
    _inherit = ['project.default.mixin', 'carpentry.budget.reservation.mixin']
    _description = "Budget Balance"

    #===== Fields =====#
    name = fields.Char()
    project_id = fields.Many2one(readonly=True)
    affectation_ids = fields.One2many(domain=[('section_res_model', '=', _name)])
    launch_ids = fields.Many2many(
        string='Launchs',
        comodel_name='carpentry.group.launch',
        compute='_compute_launch_ids',
        readonly=False,
        domain="[('project_id', '=', project_id)]",
    )
    budget_analytic_ids = fields.Many2many(
        domain="[('budget_project_ids', '=', project_id)]",
    )

    #===== Affectations methods =====#
    def _get_budget_types(self):
        return [x[0] for x in self.env['account.analytic.account']._fields['budget_type'].selection]
    
    def _compute_budget_analytic_ids(self):
        """ Budget's are computed ones if `launch_ids` are selected, else project's """
        if self.launch_ids:
            # Select launch's budgets
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

        for balance in self:
            balance.budget_analytic_ids = mapped_data.get(balance.project_id.id)

    def _has_real_affectation_matrix_changed(self, vals_list):
        """ `affectation_ids` is populated in _compute_affectation_ids, not in write() """
        return True
    
    def _get_total_by_analytic(self):
        """ Balance => budget to reserve is *all* remaining budget
            :return: Dict like {analytic_id: charged amount}
        """
        self.ensure_one()
        return self.budget_analytic_ids._get_remaining_budget_by_analytic(
            launchs=self.project_id.launch_ids, section=self
        )
