# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from collections import defaultdict

class ManufacturingOrder(models.Model):
    """ Budget Reservation on MOs """
    _name = 'mrp.production'
    _inherit = ['mrp.production', 'carpentry.budget.reservation.mixin']

    #====== Fields ======#
    affectation_ids = fields.One2many(domain=[('section_res_model', '=', _name)])
    affectation_ids_production = fields.One2many(
        domain=[('section_res_model', '=', _name), ('budget_type', '=', 'production')]
    )
    # affectation_ids_production = fields.One2many(
    #     comodel_name='carpentry.group.affectation',
    #     compute='_compute_affectation_ids_production',
    #     inverse='_inverse_affectation_ids_production',
    # )
    budget_analytic_ids = fields.Many2many(
        relation='carpentry_group_affectation_budget_mrp_analytic_rel',
        column1='production_id',
        column2='analytic_id',
        inverse='', # cancel from mixin
        store=True,
        readonly=False,
    )
    budget_analytic_ids_production = fields.Many2many(
        related='budget_analytic_ids',
        string='Budget (production)',
        readonly=False,
        domain="""[
            ('budget_project_ids', '=', project_id),
            ('budget_type', 'in', ['production'])
        ]"""
    )
    amount_budgetable = fields.Monetary(string='Total cost (components)')
    amount_gain = fields.Monetary(string='Gain (components)')
    sum_quantity_affected = fields.Float(
        string='Amount of reserved budget (components)',
        help='Sum of budget reservation (for components only)'
    )
    currency_id = fields.Many2one(related='project_id.currency_id')

    #===== Affectations configuration =====#
    def _should_move_raw_reserve_budget(self):
        return self.state not in ['cancel']
    
    def _get_component_budget_types(self):
        return ['goods', 'project_global_cost']
    
    def _get_fields_affectation_refresh(self):
        return super()._get_fields_affectation_refresh() + ['move_raw_ids', 'affectation_ids_production']

    #===== Affectations: time =====#
    def _compute_affectation_ids_production(self):
        domain = [('budget_type', '=', 'production')]
        for production in self:
            production.affectation_ids_production = production.affectation_ids.filtered_domain(domain)
    
    def _inverse_affectation_ids_production(self):
        domain = [('budget_type', '=', 'production')]
        self.affectation_ids.filtered_domain(domain).unlink()
        for production in self:
            production.affectation_ids += production.affectation_ids_production

    #===== Affectations: compute =====#
    @api.depends('move_raw_ids', 'move_raw_ids.product_id')
    def _compute_budget_analytic_ids(self):
        """ MO's budgets are updated automatically from:
            - component's analytic distribution model
            (- workcenter's analytics [STOPPED - ALY 2025-03-12]) -> now only manual

            (!) Let's be careful to keep manually chosen analytics (for workcenters)
        """
        self._set_readonly_affectation()

        to_clean = self.filtered(lambda x: not x._should_move_raw_reserve_budget())
        to_clean.budget_analytic_ids = False

        budget_types = self._get_component_budget_types()
        for mo in (self - to_clean):
            project_budgets = mo.project_id.budget_line_ids.analytic_account_id

            existing = mo.budget_analytic_ids.filtered(lambda x: x.budget_type in budget_types)._origin
            to_add = mo.move_raw_ids.analytic_ids._origin & project_budgets
            to_remove = existing - to_add
            if to_add:
                mo.budget_analytic_ids += to_add
            if to_remove:
                mo.budget_analytic_ids -= to_remove

    def _get_total_by_analytic(self):
        """ Group-sum real cost of components (& workcenter)
            :return: Dict like {analytic_id: charged amount}
        """
        self.ensure_one()
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
        budget_types = self._get_component_budget_types()
        for production in self:
            affectations_goods = production.affectation_ids.filtered(lambda x: x.group_ref and x.group_ref.budget_type in budget_types)
            production.sum_quantity_affected = sum(affectations_goods.mapped('quantity_affected'))
    
    @api.depends('move_raw_ids', 'move_raw_ids.product_id', 'move_raw_ids.stock_valuation_layer_ids')
    def _compute_amount_gain(self):
        return super()._compute_amount_gain()

    # TODO: hours
    # @api.depends('workorder_ids')
    # def _compute_amount_budgetable_workorder(self):
