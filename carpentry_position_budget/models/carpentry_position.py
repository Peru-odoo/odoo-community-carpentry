# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

class CarpentryPosition(models.Model):
    _name = 'carpentry.position'
    _inherit = ['carpentry.position', 'carpentry.group.budget.mixin']
    _rec_name = 'display_name'
    _rec_names_search = ['name']

    # import
    external_db_guid = fields.Char(string='Last External DB ID')
    warning_name = fields.Boolean(
        string='Warning Name',
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
        currency_field='currency_id',
    )

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
            lazy=False
        )
        mapped_position_name = {
            (x['project_id'][0], x['name']): x['position_ids']
            for x in rg_result
        }
        for position in self:
            sibling_ids = mapped_position_name.get((position.project_id.id, position.name), [])
            sibling_ids = [x for x in sibling_ids if x != position.id] # remove current position
            position.warning_name = len(sibling_ids)

    #===== Compute (budgets) =====#
    @api.depends(
        # 1a. products template/variants price & dates
        'position_budget_ids.analytic_account_id.timesheet_cost_history_ids',
        'position_budget_ids.analytic_account_id.timesheet_cost_history_ids.hourly_cost',
        'position_budget_ids.analytic_account_id.timesheet_cost_history_ids.starting_date',
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
