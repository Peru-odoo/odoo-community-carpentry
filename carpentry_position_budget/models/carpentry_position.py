# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

class CarpentryPosition(models.Model):
    _name = 'carpentry.position'
    _inherit = ['carpentry.position', 'carpentry.group.budget.mixin']
    _rec_name = 'display_name'

    # import
    external_db_id = fields.Integer(string='External DB ID')
    warning_name = fields.Boolean(
        compute='_compute_warning_name',
    )
    # budget
    position_budget_ids = fields.One2many(
        comodel_name='carpentry.position.budget',
        inverse_name='position_id'
    )
    budget_subtotal = fields.Monetary(
        string='Sub-total',
        compute='_compute_budgets',
        store=True,
        currency_field='currency_id',
    )

    _sql_constraints = [("name_per_project", "CHECK (1=1)", "")]

    #===== Compute (display_name) =====#
    def _compute_display_name(self):
        """ Full display_name mode for merge wizard """
        if not self._context.get('merge_wizard'):
            return super()._compute_display_name()
        
        for position in self:
            position.display_name = '{name} ({lot}) / {qty} / {range} / {descr} / {budget}' . format(
                name = position.name,
                lot = position.lot_id.name or '',
                qty = position.quantity,
                range = position.range or '',
                descr = position.description or '',
                budget = float(position.budget_total) or 0,
            )
    
    @api.depends('name')
    def _compute_warning_name(self):
        """ Detects duplicate of names, that must be allowed for import but is not wanted """
        rg_result = self.env['carpentry.position'].read_group(
            domain=[('project_id', 'in', self.project_id.ids)],
            groupby=['project_id', 'name'],
            fields=['position_ids:array_agg(id)'],
        )
        position_ids_ = []
        for x in rg_result:
            position_ids_ += x['position_ids']
        for position in self:
            position.warning_name = position.id in position_ids_


    #===== Compute (budgets) =====#
    def _get_budgets_brut_valued(self):
        """ Override from `carpentry.group.budget.mixin` """
        return self.position_budget_ids._get_position_unitary_budget(groupby_budget='detailed_type')

    @api.depends(
        # 1a. products template/variants price & dates
        'position_budget_ids.analytic_account_id.product_tmpl_id.product_variant_ids',
        'position_budget_ids.analytic_account_id.product_tmpl_id.product_variant_ids.standard_price',
        'position_budget_ids.analytic_account_id.product_tmpl_id.product_variant_ids.date_from',
        # 1b. valuations of qties -> project's budget's dates
        'project_id.budget_ids', 'project_id.budget_ids.date_from', 'project_id.budget_ids.date_to',
        # 2. position' budgets
        'position_budget_ids',
        'position_budget_ids.amount',
        # 3. position quantity
        'quantity',
    )
    def _compute_budgets(self):
        """ Just to overwrite `@api.depends(...)` """
        return super()._compute_budgets()

    def _compute_budgets_one(self, brut, valued):
        """ Because Positions are not Groupped, computed `total` is actually unitary total """
        super()._compute_budgets_one(brut, valued)
        self.budget_subtotal = self.budget_total
        self.budget_total = self.budget_subtotal * self.quantity
