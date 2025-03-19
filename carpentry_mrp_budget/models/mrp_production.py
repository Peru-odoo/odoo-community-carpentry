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
    amount_budgetable = fields.Monetary(string='Total cost (components)')
    amount_gain = fields.Monetary(string='Gain (components)')
    sum_quantity_affected = fields.Float(
        string='Amount of reserved budget (components)',
        help='Sum of budget reservation (for components only)'
    )
    currency_id = fields.Many2one(related='project_id.currency_id')

    def _should_move_raw_reserve_budget(self):
        return self.state not in ['cancel']
    
    @api.depends('budget_analytic_ids')
    def _compute_affectation_ids(self):
        """ Update budget reservation matrix on
            manual update of `budget_analytic_ids`
        """
        return super()._compute_affectation_ids()

    @api.depends('move_raw_ids', 'move_raw_ids.product_id')
    def _compute_budget_analytic_ids(self):
        """ MO's budgets are updated automatically from:
            - component's analytic distribution model
            (- workcenter's analytics [STOPPED - ALY 2025-03-12]) -> now only manual

            (!) Let's be careful to keep manually chosen analytics (for workcenters)
        """
        for mo in self:
            project_budgets = mo.project_id.budget_line_ids.analytic_account_id

            new = mo.filtered(lambda x: x._should_move_raw_reserve_budget()).move_raw_ids.analytic_ids._origin # | mo.workorder_ids.workcenter_id.costs_hour_account_id
            old = mo._origin.move_raw_ids.analytic_ids # | mo._origin.workorder_ids.workcenter_id.costs_hour_account_id
            print('new', new)
            print('old', old)
            to_add = new.filtered('is_project_budget') & project_budgets
            to_remove = old - new & old
            print('to_add', to_add)
            print('to_remove', to_remove)
            if to_add or to_remove:
                print('to_add.filtered(is_project_budget) & project_budgets', to_add.filtered('is_project_budget') & project_budgets)
                mo.budget_analytic_ids += to_add.filtered('is_project_budget') & project_budgets - to_remove

    def _get_total_by_analytic(self):
        """ Group-sum real cost of components (& workcenter)
            :return: Dict like {analytic_id: charged amount}
        """
        to_compute_move_raw = self.filtered(lambda x: x._should_move_raw_reserve_budget())
        if not to_compute_move_raw:
            return {}
        
        mapped_analytics = to_compute_move_raw._get_mapped_project_analytics()
        mapped_cost = defaultdict(float)

        # Components
        for move in to_compute_move_raw.move_raw_ids:
            if not move.analytic_distribution:
                continue

            for analytic_id, percentage in move.analytic_distribution.items():
                analytic_id = int(analytic_id)

                # Ignore cost if analytic not in project's budget
                if not analytic_id in mapped_analytics.get(move.project_id.id, []):
                    continue
                # qty in product.uom_id
                qty = move.product_uom._compute_quantity(move.product_uom_qty, move.product_id.uom_id)
                mapped_cost[analytic_id] += qty * move.sudo()._get_price_unit() * percentage / 100
        
        # Workcenter
        # for wo in self.workorder_ids:
        #     analytic = wo.workcenter_id.costs_hour_account_id
        #     # Ignore cost if analytic not in project's budget
        #     if analytic.id in mapped_analytics.get(wo.project_id.id, []):
        #         mapped_cost[analytic.id] += wo.duration_expected / 60 # in hours

        return mapped_cost

    #====== Compute amount ======#
    @api.depends('move_raw_ids', 'move_raw_ids.product_id', 'move_raw_ids.stock_valuation_layer_ids')
    def _compute_amount_budgetable(self):
        """ MO's **COMPONENTS-ONLY** cost is like for picking:
            - its moves valuation when valuated
            - else, estimation via products' prices
        """
        to_compute = self.filtered(lambda x: x._should_move_raw_reserve_budget())
        (self - to_compute).amount_budgetable = False
        if not to_compute:
            return
        
        rg_result = self.env['stock.valuation.layer'].sudo().read_group(
            domain=[('raw_material_production_id', 'in', to_compute.ids)],
            fields=['value:sum'],
            groupby=['raw_material_production_id']
        )
        mapped_svl_values = {x['raw_material_production_id'][0]: x['value'] for x in rg_result}
        for production in to_compute:
            production.amount_budgetable = abs(mapped_svl_values.get(
                production._origin.id,
                sum(production._get_total_by_analytic().values())
            ))
    
    @api.depends('affectation_ids.quantity_affected')
    def _compute_sum_quantity_affected(self):
        """ [Overwritte] `sum_quantity_affected` and `gain` are for filtered for components only (goods), not workorder (hours) """
        budget_types = ['goods', 'project_global_cost']
        for production in self:
            affectations_goods = production.affectation_ids.filtered(lambda x: x.group_ref and x.group_ref.budget_type in budget_types)
            production.sum_quantity_affected = sum(affectations_goods.mapped('quantity_affected'))
    
    @api.depends('move_raw_ids', 'move_raw_ids.product_id', 'move_raw_ids.stock_valuation_layer_ids')
    def _compute_amount_gain(self):
        return super()._compute_amount_gain()

    # TODO: hours
    # @api.depends('workorder_ids')
    # def _compute_amount_budgetable_workorder(self):
