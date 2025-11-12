# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryBudgetRemaining(models.Model):
    _inherit = ['carpentry.budget.remaining']

    #===== Fields =====#
    purchase_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Purchase Order',
        readonly=True,
    )
