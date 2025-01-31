# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.tools import float_compare
from collections import defaultdict

class ManufacturingOrder(models.Model):
    _name = 'mrp.production'
    _inherit = ['mrp.production', 'carpentry.budget.reservation.mixin']

    #====== Fields ======#
    affectation_ids = fields.One2many(domain=[('section_res_model', '=', _name)])
    warning_budget = fields.Boolean(compute='_compute_warning_budget')
    budget_analytic_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        relation='carpentry_group_affectation_budget_mrp_analytic_rel',
        column1='production_id',
        column2='analytic_id',
        string='Budgets',
        compute='_compute_budget_analytic_ids',
        inverse='', # cancel from mixin
        domain="[('budget_project_ids', '=', project_id)]",
        store=True,
        readonly=False
    )

    def _compute_warning_budget(self):
        prec = self.env['decimal.precision'].precision_get('Product Price')
        states = ['confirmed', 'progress', 'to_close', 'done']
        for mo in self:
            compare = float_compare(mo.production_duration_expected, mo.sum_quantity_affected, precision_digits=prec)
            mo.warning_budget = mo.state in states and compare != 0
    
    @api.depends('budget_analytic_ids')
    def _compute_affectation_ids(self):
        """ Update budget reservation matrix when:
            - updating stock reservation, workorders (auto)
            - manual update of `budget_analytic_ids`
        """
        self.readonly_affectation = True # tells the user to Save
        return super()._compute_affectation_ids()

    @api.depends('move_raw_ids', 'move_raw_ids.product_id', 'workorder_ids', 'workorder_ids.workcenter_id')
    def _compute_budget_analytic_ids(self):
        """ MO's budgets are from:
            - component's analytic distribution model
            - workcenter's analytics
        """
        for mo in self:
            project_budgets = mo.project_id.budget_line_ids.analytic_account_id
            components_analytics = mo.move_raw_ids.analytic_ids
            workcenter_analytics = mo.workorder_ids.workcenter_id.costs_hour_account_id
            mo.budget_analytic_ids = (components_analytics | workcenter_analytics).filtered('is_project_budget') & project_budgets

    def _get_total_by_analytic(self):
        """ Group-sum real cost of components & workcenter
            :return: Dict like {analytic_id: charged amount}
        """
        self.ensure_one()
        mapped_analytics = self._get_mapped_project_analytics()
        mapped_cost = defaultdict(float)

        # Components
        for move in self.move_raw_ids:
            if not move.analytic_distribution:
                continue

            for analytic_id, percentage in move.analytic_distribution.items():
                analytic_id = int(analytic_id)

                # Ignore cost if analytic not in project's budget
                if not analytic_id in mapped_analytics.get(move.project_id.id, []):
                    continue
                # qty in product.uom_id
                qty = move.product_uom_id._compute_quantity(move.product_uom_qty, move.product_id.uom_id)
                mapped_cost[analytic_id] += qty * move._get_price_unit() * percentage / 100
        
        # Workcenter
        for wo in self.workorder_ids:
            analytic = wo.workcenter_id.costs_hour_account_id
            # Ignore cost if analytic not in project's budget
            if analytic.id in mapped_analytics.get(wo.project_id.id, []):
                mapped_cost[analytic.id] += wo.duration_expected / 60 # in hours

        return mapped_cost
