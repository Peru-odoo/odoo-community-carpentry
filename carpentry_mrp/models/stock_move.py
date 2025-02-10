# -*- coding: utf-8 -*-

from odoo import models, fields, exceptions, _

class StockMoveLine(models.Model):
    _inherit = ['stock.move.line']

    launch_ids = fields.Many2many(related='move_id.launch_ids')

class StockMove(models.Model):
    _inherit = ['stock.move']

    launch_ids = fields.Many2many(related='picking_id.launch_ids')

    # def write(self, vals):
    #     """ Move to `done` the components of MO as soon as they have `quantity_done` """
    #     res = super().write(vals)
    #     if 'quantity_done' in vals:
    #         moves_mrp = self.filtered(lambda x: x.raw_material_production_id and x.quantity_done)
    #         moves_mrp._action_done(cancel_backorder=False)
    #     return res
