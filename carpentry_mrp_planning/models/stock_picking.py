# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class StockPicking(models.Model):
    _inherit = ['stock.picking']
