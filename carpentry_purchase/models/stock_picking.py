# -*- coding: utf-8 -*-

from odoo import models, fields, exceptions, _

class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ['stock.picking', 'project.default.mixin']
