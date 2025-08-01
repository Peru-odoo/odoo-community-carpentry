# -*- coding: utf-8 -*-

from odoo import models, fields

class PurchaseOrderLine(models.Model):
    _inherit = ['purchase.order.line']
    
    project_id = fields.Many2one(
        related='order_id.project_id',
        store=True,
    )
