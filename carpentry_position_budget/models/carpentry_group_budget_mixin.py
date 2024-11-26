# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

class CarpentryGroupBudgetMixin(models.AbstractModel):
    _name = 'carpentry.group.budget.mixin'
    _description = 'Carpentry Group Budget Mixin'
    # _inherit = ['carpentry.group.mixin']

    project_id = fields.Many2one(
        comodel_name='project.project'
    )
    currency_id = fields.Many2one(
        related='project_id.company_id.currency_id'
    )

    # budget sums
    # only the fields relevant for Carpentry Group (ie. budgets from affectation)
    # but some other can be added here and in `_compute_budgets_one()`: see Project and Positions
    budget_prod = fields.Float(
        # in (h)
        string='Prod',
        compute='_compute_budgets',
        store=True,
    )
    budget_install = fields.Float(
        # in (h)
        string='Install',
        compute='_compute_budgets',
        store=True,
    )
    # no 'office' because not in positions
    budget_goods = fields.Monetary(
        # in (€)
        string='Goods',
        compute='_compute_budgets',
        store=True,
        currency_field='currency_id',
    )
    budget_total = fields.Monetary(
        string='Total',
        compute='_compute_budgets',
        store=True,
        currency_field='currency_id',
    )
    
    
    #===== Compute (budgets) =====#
    def _get_budgets_brut_valued(self):
        return self.env['carpentry.position.budget'].sum(
            quantities=self._get_quantities(),
            groupby_group=['group_id'],
            groupby_budget='detailed_type',
            domain_budget=self._get_domain_budget_ids()
        )
    
    def _get_domain_budget_ids(self):
        """ [For overwriting] Optional. Example: return [('product_id', 'in', ...)] """
        return []
    
    def _compute_budgets_one(self, brut, valued):
        """ Allows to be overriden, e.g. for position to change `total` and `subtotal` computation """
        self.ensure_one()
        self.budget_prod = self._get_budget_one(brut, 'service_prod')
        self.budget_install = self._get_budget_one(brut, 'service_install')
        self.budget_goods = self._get_budget_one(valued, ['consu', 'storable'])
        self.budget_total = self._get_budget_one(valued, ['service_prod', 'service_install', 'consu', 'storable'])
    
    def _get_budget_one(self, budget, detailed_types):
        detailed_types = [detailed_types] if isinstance(detailed_types, str) else detailed_types
        return sum([
            budget.get(self.id, {}).get(x, 0.0)
            for x in detailed_types
        ])

    @api.depends(
        # 1a. products template/variants price & dates
        'project_id.position_budget_ids.analytic_account_id.product_tmpl_id.product_variant_ids',
        'project_id.position_budget_ids.analytic_account_id.product_tmpl_id.product_variant_ids.standard_price',
        'project_id.position_budget_ids.analytic_account_id.product_tmpl_id.product_variant_ids.date_from',
        # 1b. valuations of qties -> budget's dates
        'project_id.budget_ids', 'project_id.budget_ids.date_from', 'project_id.budget_ids.date_to',
        # 2. positions' budgets
        'project_id.position_budget_ids',
        'project_id.position_budget_ids.amount',
        # 3. positions affectations
        'affectation_ids',
        'affectation_ids.quantity_affected'
    )
    def _compute_budgets(self):
        if self._context.get('import_budget_no_compute'):
            return
        
        brut, valued = self._get_budgets_brut_valued()
        for group in self:
            group._compute_budgets_one(brut, valued)
