# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

class SaleOrderLine(models.Model):
    _inherit = ['sale.order.line']

    budget_updated = fields.Boolean(
        string='Budget updated?',
        default=False,
        help="Has project's budget been updated?",
    )
