# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from collections import defaultdict

class StockPicking(models.Model):
    """ Budget Reservation on pickings """
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'carpentry.budget.reservation.mixin']

    # cancel from mixin: `analytic_distribution` is not writable but computed on stock_move
    budget_analytic_ids = fields.Many2many(inverse='')
    amount_budgetable = fields.Monetary(string='Total Cost',)
    currency_id = fields.Many2one(related='project_id.currency_id')

    @api.depends('move_ids', 'move_ids.product_id')
    def _compute_affectation_ids(self):
        """ Inherite to add fields in @api.depends """
        return super()._compute_affectation_ids()

    @api.depends('move_ids', 'move_ids.product_id')
    def _compute_budget_analytic_ids(self):
        """ Picking budgets are from moves' analytic distribution """
        for picking in self:
            project_budgets = picking.project_id.budget_line_ids.analytic_account_id
            picking.budget_analytic_ids = picking.move_ids.analytic_ids.filtered('is_project_budget') & project_budgets
    
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
