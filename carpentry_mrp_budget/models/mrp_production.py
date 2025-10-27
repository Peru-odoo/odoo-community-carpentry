# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.tools import float_round
from collections import defaultdict

class ManufacturingOrder(models.Model):
    """ Budget Reservation on MOs """
    _name = 'mrp.production'
    _inherit = ['mrp.production', 'carpentry.budget.mixin']
    _carpentry_budget_notebook_page_xpath = '//page[@name="components"]'
    _carpentry_budget_sheet_name = 'Budget (components)'
    _carpentry_budget_last_valuation_step = _('products revaluation')

    #====== Fields ======#
    reservation_ids = fields.One2many(domain=[('section_res_model', '=', _name)])
    reservation_ids_components = fields.One2many(
        comodel_name='carpentry.budget.reservation',
        inverse_name='section_id',
        domain=[('section_res_model', '=', _name), ('budget_type', 'in', ['goods', 'other'])],
        context={'active_test': False},
    )
    reservation_ids_workorders = fields.One2many(
        comodel_name='carpentry.budget.reservation',
        inverse_name='section_id',
        domain=[('section_res_model', '=', _name), ('budget_type', 'in', ['production'])],
        context={'active_test': False},
    )
    budget_analytic_ids = fields.Many2many(
        relation='carpentry_budget_mrp_analytic_rel',
        column1='production_id',
        column2='analytic_id',
    )
    budget_analytic_ids_workorders = fields.Many2many(
        comodel_name='account.analytic.account',
        compute='_compute_budget_analytic_ids_workorders',
        inverse='_inverse_budget_analytic_ids_workorders',
        string='Budget (work orders)',
        domain="""[
            ('budget_project_ids', '=', project_id),
            ('budget_type', 'in', ['production'])
        ]"""
    )
    total_budget_reserved = fields.Float(
        string='Budget (components)',
        help='Sum of budget reservation for components only',
        store=True, # needed in expense report
    )
    total_budget_reserved_workorders = fields.Float(
        string='Budget (workorders)',
        help='Sum of budget reservation in hours for workorders only',
        compute='_compute_budget_totals',
        compute_sudo=True,
    )
    difference_workorder_duration_budget = fields.Float(
        compute='_compute_budget_totals',
        compute_sudo=True,
    )
    total_expense_valued = fields.Monetary(string='Total cost (components)', compute_sudo=True,)
    total_expense_valued_workorders = fields.Monetary(
        string='Total cost (work orders)',
        compute='_compute_budget_totals',
        compute_sudo=True,
    )
    budget_unit_workorders = fields.Char(default='h')
    amount_gain = fields.Monetary(string='Gain (components)', compute_sudo=True,)
    amount_loss = fields.Monetary(compute_sudo=True,)
    amount_gain_workorders = fields.Monetary(
        compute='_compute_budget_totals',
        compute_sudo=True,
    )
    other_expense_ids = fields.Many2many(compute_sudo=True,)
    other_expense_ids_workorders = fields.Many2many(
        comodel_name='carpentry.budget.expense',
        string='Other expenses (components)',
        compute='_compute_budget_totals',
        compute_sudo=True,
    )
    date_budget_workorders = fields.Date(
        compute='_compute_date_budget',
        string='Last date time',
        store=True,
    )
    # -- view fields --
    show_gain = fields.Boolean(compute_sudo=True,)
    is_temporary_gain = fields.Boolean(compute_sudo=True,)
    show_gain = fields.Boolean(compute_sudo=True,)
    text_no_reservation = fields.Char(compute='_compute_budget_totals',compute_sudo=True,)
    total_budgetable = fields.Float(compute_sudo=True,)
    total_budgetable_workorders = fields.Float(compute='_compute_budget_totals', compute_sudo=True,)
    show_gain_workorders = fields.Boolean(compute='_compute_budget_totals', compute_sudo=True,)
    text_no_reservation_workorders = fields.Char(compute='_compute_budget_totals', compute_sudo=True,)
    is_temporary_gain_workorders = fields.Boolean(
        store=False,
        default=False,
    )

    #===== Compute =====#
    def _compute_state(self):
        """ Ensure `reservation_ids.active` follows `mrp_production.state`,
            which is a computed stored field and thus not catched in `write`
        """
        res = super()._compute_state()
        self.reservation_ids._compute_section_fields()
        return res
    
    @api.depends('budget_analytic_ids')
    def _compute_budget_analytic_ids_workorders(self):
        budget_types_workorders = self._get_workorder_budget_types()
        for mo in self:
            mo.budget_analytic_ids_workorders = mo.budget_analytic_ids.filtered(
                lambda x: x.budget_type in budget_types_workorders
            )
    def _inverse_budget_analytic_ids_workorders(self):
        """ Populate workorders budget center in main field budget_analytic_ids,
            without refreshing component's `amount_reserved` 
        """
        self = self.with_context(budget_analytic_ids_workorders_inverse=True)
        budget_types_workorders = self._get_workorder_budget_types()
        for mo in self:
            existing = mo.budget_analytic_ids.filtered(
                lambda x: x.budget_type in budget_types_workorders
            )
            to_add = mo.budget_analytic_ids_workorders._origin - existing
            to_remove = existing - mo.budget_analytic_ids_workorders._origin

            if to_add:
                mo.budget_analytic_ids += to_add
            if to_remove:
                mo.budget_analytic_ids -= to_remove
        
        mo.invalidate_recordset(['budget_analytic_ids']) # ensure correct value in next logics
    
    #===== Budgets customization =====#
    def _auto_update_budget_distribution(self):
        """ Don't update components amounts while update workorders budgets """
        if self._context.get('budget_analytic_ids_workorders_inverse'):
            return
        
        super()._auto_update_budget_distribution()

    #===== Budgets configuration =====#
    def _get_budget_types(self):
        return self._get_workorder_budget_types() + self._get_component_budget_types()
    def _get_workorder_budget_types(self):
        return ['production']
    def _get_component_budget_types(self):
        return ['goods', 'other']
    
    def _get_reservations_auto_update(self):
        """ Filter reservations of workorders so their amount is never updated """
        return self.reservation_ids.filtered(
            lambda x: x.budget_type in self._get_component_budget_types()
        )

    def _get_fields_budget_reservation_refresh(self):
        return (
            super()._get_fields_budget_reservation_refresh()
            + ['move_raw_ids']
        )

    def _get_domain_is_temporary_gain(self):
        return [('state', '!=', 'done'),]
    
    #===== Budget reservation: date & compute =====#
    @api.depends(
        'date_planned_start', 'date_finished',
        'workorder_ids.time_ids.date_end',
    )
    def _compute_date_budget(self):
        """ Manages both `date_budget` for components and workorders """
        for mo in self:
            mo.date_budget = mo.date_finished or mo.date_planned_start
            dates_end = mo.workorder_ids.time_ids.filtered('date_end').mapped('date_end')
            mo.date_budget_workorders = max(dates_end) if bool(dates_end) else False
            
            # update reservations' dates
            reservations_components = mo._get_reservations_auto_update()
            reservations_components.date = mo.date_budget
            (mo.reservation_ids - reservations_components).date = mo.date_budget_workorders

    def _get_auto_budget_analytic_ids(self):
        """ Only for components
            For workcenters: keep manually chosen budgets
        """
        Analytic = self.env['account.analytic.account']
        workcenter_budgets = self.budget_analytic_ids.filtered(
            lambda x: x.budget_type not in self._get_component_budget_types()
        )
        components_budgets = self.move_raw_ids.analytic_account_ids if self.can_reserve_budget else Analytic
        return (workcenter_budgets + components_budgets)._origin.ids

    #====== Compute amount ======#
    def _compute_budget_totals(self):
        super()._compute_budget_totals()
        prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for mo in self:
            mo.difference_workorder_duration_budget = float_round(
                mo.production_duration_hours_expected -
                mo.total_budget_reserved_workorders,
                precision_digits = prec
            )
    def _compute_budget_totals_one(self, totals, expense_ids, prec, pivot_analytic_to_budget_type):
        """ 1. Split `totals` and `expense_ids` between components and workorders
            2. Computes both totals
        """
        # 1.
        components_budget_types = self._get_component_budget_types()
        totals_workorders, expense_ids_workorders = {}, {}
        for aac_id in totals.copy():
            budget_type = pivot_analytic_to_budget_type.get(aac_id)
            if budget_type not in components_budget_types:
                totals_workorders[aac_id] = totals.pop(aac_id)
                if aac_id in expense_ids:
                    expense_ids_workorders[aac_id] = expense_ids.pop(aac_id)

        # 2.
        super()._compute_budget_totals_one(totals, expense_ids, prec)
        super()._compute_budget_totals_one(totals_workorders, expense_ids_workorders, prec, field_suffix='_workorders')


    #===== Views =====#
    def _get_view_carpentry_config(self):
        """ Add workorders tab """
        res = super()._get_view_carpentry_config()
        res[0]['params'] |= {
            'model_description': _('Components'),
            'fields_suffix': '_components',
            'budget_types': [x for x in self._get_component_budget_types()],
        }
        return res + [
            {
                'templates': {
                    'alert_banner': self._carpentry_budget_alert_banner_xpath,
                    'notebook_page': '//page[@name="operations"]',
                },
                'params': {
                    'model_name': self._name,
                    'model_description': _('Work Orders'),
                    'fields_suffix': '_workorders',
                    'budget_types': [x for x in self._get_budget_types() if x not in self._get_component_budget_types()],
                    'budget_choice': self._carpentry_budget_choice,
                    'sheet_name': _('Budget (work orders)'),
                    'last_valuation_step': False,
                    'button_refresh': False,
                }
            }
        ,]
