# -*- coding: utf-8 -*-

from odoo import models, fields, api
from collections import defaultdict

class CarpentryGroupBudgetMixin(models.AbstractModel):
    """ Budget sums from Affectations
        Relevant for Phases, Launches, Positions (and Project)
    """
    _name = 'carpentry.group.budget.mixin'
    _description = 'Carpentry Group Budget Mixin'

    project_id = fields.Many2one(comodel_name='project.project')
    currency_id = fields.Many2one(related='project_id.company_id.currency_id')
    # in (h)
    budget_office = fields.Float(string='Office', compute='_compute_budgets')
    budget_production = fields.Float(string='Prod', compute='_compute_budgets')
    budget_installation = fields.Float(string='Install', compute='_compute_budgets')
    # in (€)
    budget_goods = fields.Monetary(string='Goods', compute='_compute_budgets', currency_field='currency_id')
    budget_project_global_cost = fields.Monetary(string='Other costs', compute='_compute_budgets', currency_field='currency_id')
    # total
    budget_total = fields.Monetary(string='Total', compute='_compute_budgets', currency_field='currency_id')
    
    
    #===== Compute (budgets) =====#
    def _get_budgets_totals(self):
        """ Return brut & valued in a tuple like:
            {group_id: valued amount}
        """
        field = self._name.replace('carpentry.', '').replace('group.', '') + '_id'
        rg_result = self.env['carpentry.budget.available.valued']._read_group(
            domain=[(field, 'in', self.ids), ('group_res_model', '=', self._name)],
            groupby=[field, 'budget_type'],
            fields=['subtotal:sum', 'value:sum', 'project_id'],
            lazy=False,
        )
        brut, valued = defaultdict(dict), defaultdict(dict)
        for data in rg_result:
            brut[data[field][0]][data['budget_type']] = data['subtotal']
            valued[data[field][0]][data['budget_type']] = data['value']
        return brut, valued
    
    def _get_domain_budget_ids(self):
        """ [For overwriting] Optional """
        return []
    
    def _compute_budgets_one(self, brut, valued):
        """ Allows to be overriden, e.g. for position to change `total` and `subtotal` computation """
        self.ensure_one()
        self.budget_office =              self._get_budget_one(brut,   ['office'])
        self.budget_production =          self._get_budget_one(brut,   ['production'])
        self.budget_installation =        self._get_budget_one(brut,   ['installation'])
        self.budget_goods =               self._get_budget_one(valued, ['goods'])
        self.budget_project_global_cost = self._get_budget_one(valued, ['project_global_cost'])
        self.budget_total =               self._get_budget_one(valued,
            ['office', 'production', 'installation', 'goods', 'project_global_cost']
        )
    
    def _get_budget_one(self, budget, budget_types):
        return sum([
            budget.get(self.id, {}).get(x, 0.0)
            for x in budget_types
        ])

    def _compute_budget_fields(self):
        return [
            # 1a. products template/variants price & dates
            'project_id.position_budget_ids.analytic_account_id.timesheet_cost_history_ids',
            'project_id.position_budget_ids.analytic_account_id.timesheet_cost_history_ids.hourly_cost',
            'project_id.position_budget_ids.analytic_account_id.timesheet_cost_history_ids.starting_date',
            # 1b. valuations of qties -> budget's dates
            'project_id.budget_ids', 'project_id.budget_ids.date_from', 'project_id.budget_ids.date_to',
            # 2. positions' budgets
            'project_id.position_budget_ids',
            'project_id.position_budget_ids.amount',
            # 3. positions affectations
            'affectation_ids',
            'affectation_ids.quantity_affected'
        ]
    
    @api.depends(lambda self: self._compute_budget_fields())
    def _compute_budgets(self):
        if self._context.get('import_budget_no_compute'):
            return
    
        brut, valued = self._get_budgets_totals()
        for group in self:
            group.sudo()._compute_budgets_one(brut, valued)
