# -*- coding: utf-8 -*-

from odoo import api, models, fields, exceptions, _

class StockPicking(models.Model):
    """ And `production_id` on picking via the procurement group """
    _inherit = ['stock.picking']

    production_id = fields.Many2one(
        comodel_name='mrp.production',
        string='Manufacturing Order',
        compute='_compute_production_id'
    )
    
    @api.depends(
        'move_ids.production_id',
        'move_ids.raw_material_production_id',
        'move_ids.created_production_id'
    )
    def _compute_production_id(self):
        for picking in self:
            moves = picking.move_ids
            picking.production_id = (
                moves.production_id or
                moves.raw_material_production_id or
                moves.created_production_id
            )
