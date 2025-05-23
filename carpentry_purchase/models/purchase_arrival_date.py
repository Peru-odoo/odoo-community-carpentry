# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command

class PurchaseArrivalDate(models.Model):
    _inherit = ['purchase.arrival.date']

    project_id = fields.Many2one(
        related='order_id.project_id',
    )
