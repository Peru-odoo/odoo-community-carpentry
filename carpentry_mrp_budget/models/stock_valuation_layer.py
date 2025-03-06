# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class StockValuationLayer(models.Model):
    _inherit = ['stock.valuation.layer']

    project_id = fields.Many2one(
        related='stock_move_id.project_id',
        store=True,
        index=True,
    )
