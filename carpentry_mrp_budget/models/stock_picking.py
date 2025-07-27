# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from collections import defaultdict
from odoo.osv import expression

class StockPicking(models.Model):
    """ Budget Reservation on pickings """
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'carpentry.budget.reservation.mixin']

    #====== Fields ======#
    affectation_ids = fields.One2many(domain=[('section_res_model', '=', _name)])
    budget_analytic_ids = fields.Many2many(
        relation='carpentry_group_affectation_budget_picking_analytic_rel',
        column1='picking_id',
        column2='analytic_id',
        inverse='', # cancel from mixin
        store=True,
        readonly=False,
    )
    amount_budgetable = fields.Monetary(string='Total Cost')
    currency_id = fields.Many2one(related='project_id.currency_id')
    can_reserve_budget = fields.Boolean(
        string='Project-related expense',
        compute='_compute_can_reserve_budget',
        search='_search_can_reserve_budget',
    )

    #===== Compute =====#
    @api.depends('state', 'picking_type_code', 'purchase_id')
    def _compute_can_reserve_budget(self):
        for move in self:
            move.can_reserve_budget = move._can_reserve_budget()
    @api.model
    def _search_can_reserve_budget(self, operator, value):
        domain = [
            ('state', 'not in', ['cancel']),
            ('purchase_id', '=', False),
            ('picking_type_code', '=', 'outgoing')
        ]

        if (operator == '=' and value) or (operator == '!=' and not value):
            return domain
        else:
            return expression.distribute_not([domain])
    def _can_reserve_budget(self):
        """ Prevent budget reservation on picking coming from:
            - internal, incoming, fab (returns from sconstruction field)
            - purchase orders
            - manufacturing orders
        """
        return (
            self.state not in ['cancel'] and
            not self.purchase_id and
            self.picking_type_code == 'outgoing'
        )
    
    def _is_quantity_affected_valued(self):
        return True
    
    #===== Affectations configuration =====#
    def _get_budget_types(self):
        return ['goods', 'project_global_cost']
    
    def _get_fields_affectation_refresh(self):
        return super()._get_fields_affectation_refresh() + ['move_ids']

    @api.depends('scheduled_date', 'date_done')
    def _compute_date_budget(self):
        for picking in self:
            if picking.state == 'done':
                picking.date_budget = picking.date_done
            else:
                picking.date_budget = picking.scheduled_date
        return super()._compute_date_budget()

    #===== Affectations: compute =====#
    @api.depends('move_ids', 'move_ids.product_id')
    def _compute_budget_analytic_ids(self):
        """ Update budgets list when adding product in `Operations` tab """
        to_clean = self.filtered(lambda x: not x.can_reserve_budget)
        to_clean.budget_analytic_ids = False

        to_compute = (self - to_clean).filtered('project_id')
        if to_compute:
            mapped_analytics = self._get_mapped_project_analytics()
            
            for picking in to_compute:
                project_budgets = set(mapped_analytics.get(picking.project_id.id, []))
                picking.budget_analytic_ids = list(
                    set(picking.move_ids._get_analytic_ids()._origin.filtered('is_project_budget').ids)
                    & project_budgets
                )
        
        return super()._compute_budget_analytic_ids()
    
    def _get_total_by_analytic(self):
        """ Group-sum price of move
            :return: Dict like {analytic_id: charged amount}
        """
        to_compute = self.filtered(lambda x: x.can_reserve_budget)
        if not to_compute:
            return {}
        
        mapped_analytics = to_compute._get_mapped_project_analytics()
        mapped_price = defaultdict(float)

        for move in to_compute.move_ids:
            if not move.analytic_distribution:
                continue
            
            for analytic_id, percentage in move.analytic_distribution.items():
                analytic_id = int(analytic_id)

                # Ignore cost if analytic not in project's budget
                if analytic_id in mapped_analytics.get(move.project_id.id, []):
                    qty = move.product_uom._compute_quantity(move.product_uom_qty, move.product_id.uom_id) # qty in product.uom_id
                    unit_price = abs(
                        move.product_id.standard_price
                        if move.picking_id.state in ['waiting', 'confirm', 'assigned']
                        else move._get_price_unit()
                    )
                    mapped_price[analytic_id] += qty * unit_price * percentage / 100
        return mapped_price

    #====== Compute amount ======#
    @api.depends(
        'move_ids', 'move_ids.product_id', 'move_ids.standard_price',
        'move_ids.price_unit', 'move_ids.stock_valuation_layer_ids',
    )
    def _compute_amount_budgetable(self):
        """ Picking's cost is:
            - its moves valuation when valuated
            - else, estimation via products' prices
        """
        to_compute = self.filtered(lambda x: x.can_reserve_budget)
        (self - to_compute).amount_budgetable = False
        if not to_compute:
            return
        
        rg_result = self.env['stock.valuation.layer'].sudo().read_group(
            domain=[('stock_picking_id', 'in', to_compute.ids)],
            fields=['value:sum'],
            groupby=['stock_picking_id']
        )
        mapped_svl_values = {x['stock_picking_id'][0]: x['value'] for x in rg_result}
        for picking in to_compute:
            picking.amount_budgetable = abs(mapped_svl_values.get(
                picking._origin.id,
                sum(picking._get_total_by_analytic().values())
            ))

    @api.depends('move_ids', 'move_ids.product_id', 'move_ids.stock_valuation_layer_ids')
    def _compute_amount_gain(self):
        return super()._compute_amount_gain()
