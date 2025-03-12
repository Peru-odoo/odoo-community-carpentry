# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from collections import defaultdict

class ManufacturingOrder(models.Model):
    """ Budget Reservation on MOs """
    _name = 'mrp.production'
    _inherit = ['mrp.production', 'carpentry.budget.reservation.mixin']

    #====== Fields ======#
    affectation_ids = fields.One2many(domain=[('section_res_model', '=', _name)])
    budget_analytic_ids = fields.Many2many(
        relation='carpentry_group_affectation_budget_mrp_analytic_rel',
        column1='production_id',
        column2='analytic_id',
        inverse='', # cancel from mixin
        store=True,
        readonly=False,
    )
    amount_budgetable = fields.Monetary(string='Total Cost')
    currency_id = fields.Many2one(related='project_id.currency_id')
    
    @api.depends('budget_analytic_ids')
    def _compute_affectation_ids(self):
        """ Update budget reservation matrix on
            manual update of `budget_analytic_ids`
        """
        return super()._compute_affectation_ids()

    @api.depends('move_raw_ids', 'move_raw_ids.product_id')
    def _compute_budget_analytic_ids(self):
        """ MO's budgets are from:
            - component's analytic distribution model
            (- workcenter's analytics [STOPPED - ALY 2025-03-12]) -> now only manual
        """
        for mo in self:
            project_budgets = mo.project_id.budget_line_ids.analytic_account_id

            new = mo.move_raw_ids.analytic_ids # | mo.workorder_ids.workcenter_id.costs_hour_account_id
            old = mo._origin.move_raw_ids.analytic_ids # | mo._origin.workorder_ids.workcenter_id.costs_hour_account_id
            to_add = new - new & old
            to_remove = old - new & old
            mo.budget_analytic_ids = to_add.filtered('is_project_budget') & project_budgets - to_remove

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

    #====== Compute amount ======#
    @api.depends('move_raw_ids', 'move_raw_ids.product_id', 'move_raw_ids.stock_valuation_layer_ids') # TODO: hours
    def _compute_amount_budgetable(self):
        """ MO's cost is:
            - its moves + hours valuation when valuated 
            - else, estimation via products' & hours prices
        """
        pass
        # TODO
        # rg_result = self.env['stock.valuation.layer'].read_group(
        #     domain=[('raw_material_production_id', 'in', self.ids)],
        #     fields=['value:sum'],
        #     groupby=['raw_material_production_id']
        # )
        # mapped_svl_values = {x['raw_material_production_id'][0]: x['value'] for x in rg_result}
        # for picking in self:
        #     picking.amount_budgetable = mapped_svl_values.get(
        #         picking._origin.id,
        #         sum(picking._get_total_by_analytic().values())
        #     )

    @api.depends('move_raw_ids', 'move_raw_ids.product_id', 'move_raw_ids.stock_valuation_layer_ids') # TODO: hours
    def _compute_amount_gain(self):
        return super()._compute_amount_gain()
