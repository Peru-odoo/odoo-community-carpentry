# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

class SaleOrderLine(models.Model):
    _inherit = ['sale.order.line']

    project_id = fields.Many2one(
        related='order_id.project_id',
        store=True
    )

    validated = fields.Boolean(
        string='Validated?',
        default=False,
        readonly=False,
        help='Is the amount validated with client?'
    )
