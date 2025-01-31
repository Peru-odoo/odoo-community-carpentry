# -*- coding: utf-8 -*-

from odoo import models, fields, exceptions, _

class StockMove(models.Model):
    _inherit = ['stock.move']

    launch_ids = fields.Many2many(
        related='picking_id.launch_ids'
    )

class StockMoveLine(models.Model):
    _inherit = ['stock.move.line']

    launch_ids = fields.Many2many(
        related='move_id.launch_ids'
    )
