# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from collections import defaultdict

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

    @api.depends('budget_analytic_ids')
    def _compute_affectation_ids(self):
        """ Update budget reservation matrix on
            manual update of `budget_analytic_ids`
        """
        return super()._compute_affectation_ids()

    @api.depends('move_ids', 'move_ids.product_id')
    def _compute_budget_analytic_ids(self):
        """ Picking budgets are from moves' analytic distribution """
        print('=== _compute_budget_analytic_ids ===')
        self.flush_recordset()
        self.picking_ids.flush_recordset()
        self.picking_ids.analytic_ids.flush_recordset()
        for picking in self:
            project_budgets = picking.project_id._origin.budget_line_ids.analytic_account_id
            print('project_budgets', project_budgets)
            print('picking', picking)
            print('picking.move_ids', picking.move_ids)
            print('picking.move_ids.read()', picking.move_ids.read(['analytic_ids']))
            print('picking.move_ids.analytic_ids._origin', picking.move_ids.analytic_ids._origin)
            print('picking.move_ids.analytic_ids._origin.filtered', picking.move_ids.analytic_ids._origin.filtered('is_project_budget'))
            picking.budget_analytic_ids = picking.move_ids.analytic_ids._origin.filtered('is_project_budget') & project_budgets
    
    def _get_total_by_analytic(self):
        """ Group-sum price of move
            :return: Dict like {analytic_id: charged amount}
        """
        self.ensure_one()
        mapped_analytics = self._get_mapped_project_analytics()
        mapped_price = defaultdict(float)

        for move in self.move_ids:
            if not move.analytic_distribution:
                continue
            # TODO : {} si pas sortant
            for analytic_id, percentage in move.analytic_distribution.items():
                analytic_id = int(analytic_id)

                # Ignore cost if analytic not in project's budget
                if analytic_id in mapped_analytics.get(move.project_id.id, []):
                    qty = move.product_uom._compute_quantity(move.product_uom_qty, move.product_id.uom_id) # qty in product.uom_id
                    mapped_price[analytic_id] += qty * move._get_price_unit() * percentage / 100
        
        return mapped_price

    #====== Compute amount ======#
    @api.depends('move_ids', 'move_ids.product_id', 'move_ids.stock_valuation_layer_ids')
    def _compute_amount_budgetable(self):
        """ Picking's cost is:
            - its moves valuation when valuated
            - else, estimation via products' prices
        """
        rg_result = self.env['stock.valuation.layer'].read_group(
            domain=[('stock_picking_id', 'in', self.ids)],
            fields=['value:sum'],
            groupby=['stock_picking_id']
        )
        mapped_svl_values = {x['stock_picking_id'][0]: x['value'] for x in rg_result}
        for picking in self:
            picking.amount_budgetable = mapped_svl_values.get(
                picking._origin.id,
                sum(picking._get_total_by_analytic().values())
            )

    @api.depends('move_ids', 'move_ids.product_id', 'move_ids.stock_valuation_layer_ids')
    def _compute_amount_gain(self):
        return super()._compute_amount_gain()
