# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from collections import defaultdict

class CarpentryAffectationMixin(models.AbstractModel):
    """ Budget sums from Affectations
        Relevant for Phases, Launches, Positions (and Project)
    """
    _inherit = ["carpentry.affectation.mixin"]

    project_id = fields.Many2one(comodel_name='project.project',)
    currency_id = fields.Many2one(related='project_id.company_id.currency_id')
    # in (h)
    budget_service = fields.Float(string='Service', compute='_compute_budgets')
    budget_production = fields.Float(string='Prod', compute='_compute_budgets')
    budget_installation = fields.Float(string='Install', compute='_compute_budgets')
    # in (€)
    budget_goods = fields.Monetary(string='Goods', compute='_compute_budgets', currency_field='currency_id')
    budget_other = fields.Monetary(string='Other costs', compute='_compute_budgets', currency_field='currency_id')
    # total
    budget_total = fields.Monetary(string='Total', compute='_compute_budgets', currency_field='currency_id')
    
    #===== CRUD =====#
    def unlink(self):
        """ Unlink affectations by ORM, to trigger
            `_clean_reservation_and_constrain_budget` if needed
        """
        self.affectation_ids.children_ids.unlink()
        self.affectation_ids.unlink()
        return super().unlink()
    
    #===== Compute (budgets) =====#
    def _get_budgets_totals(self):
        """ Return brut & valued in a tuple like:
            {group_id: valued amount}
        """
        field = self._name.replace('carpentry.', '').replace('group.', '') + '_id'
        rg_result = self.env['carpentry.budget.available']._read_group(
            domain=[(field, 'in', self.ids), ('group_res_model', '=', self._name)],
            groupby=[field, 'budget_type'],
            fields=['amount_subtotal:sum', 'amount_subtotal_valued:sum', 'project_id'],
            lazy=False,
        )
        brut, valued = defaultdict(dict), defaultdict(dict)
        for x in rg_result:
            brut[x[field][0]][x['budget_type']] = x['amount_subtotal']
            valued[x[field][0]][x['budget_type']] = x['amount_subtotal_valued']
        return brut, valued
    
    def _get_budget_one(self, budget, budget_types):
        return sum([
            budget.get(self.id, {}).get(x, 0.0)
            for x in budget_types
        ])

    def _get_compute_budget_fields(self):
        return [
            # 1a. products template/variants price & dates
            'project_id.position_budget_ids.analytic_account_id.timesheet_cost_history_ids',
            'project_id.position_budget_ids.analytic_account_id.timesheet_cost_history_ids.hourly_cost',
            'project_id.position_budget_ids.analytic_account_id.timesheet_cost_history_ids.starting_date',
            # 1b. valuations of qties -> budget's dates
            'project_id.budget_ids', 'project_id.budget_ids.date_from', 'project_id.budget_ids.date_to',
            # 2. positions' budgets
            'project_id.position_budget_ids',
            'project_id.position_budget_ids.amount_unitary',
            # 3. positions affectations
            'affectation_ids',
            'affectation_ids.quantity_affected',
        ]
    @api.depends(lambda self: self._get_compute_budget_fields())
    def _compute_budgets(self):
        if self._context.get('import_budget_no_compute'):
            return
    
        brut, valued = self._get_budgets_totals()

        for group in self:
            group.sudo()._compute_budgets_one(brut, valued)

    def _compute_budgets_one(self, brut, valued):
        self.ensure_one()
        self.budget_service =       self._get_budget_one(brut,   ['service'])
        self.budget_production =    self._get_budget_one(brut,   ['production'])
        self.budget_installation =  self._get_budget_one(brut,   ['installation'])
        self.budget_goods =         self._get_budget_one(valued, ['goods'])
        self.budget_other =         self._get_budget_one(valued, ['other'])

        budget_types = [
            x[0] for x in
            self.env['account.analytic.account'].fields_get()['budget_type']['selection']
        ]
        self.budget_total = self._get_budget_one(valued, budget_types)
        
    
    #===== Actions & buttons =====#
    def action_open_budget_available(self):
        """ Opens available budgets (from the form of a phase or launch) """
        field = self._name.replace('carpentry.group.', '') + '_id' # launch_id or phase_id

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'carpentry.budget.available',
            'name': _("Available budgets (by position)"),
            'view_mode': 'pivot,tree',
            'context': {
                'search_default_filter_groupby_position': 1,
                'display_model_shortname': 1,
            },
            'domain': [(field, '=', self.id)]
        }
        return action
