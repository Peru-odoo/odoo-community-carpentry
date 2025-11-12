# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryBudgetRemaining(models.Model):
    _inherit = ['carpentry.budget.remaining']

    #===== Fields =====#
    production_id = fields.Many2one(
        comodel_name='mrp.production',
        string='Manufacturing Order',
        readonly=True,
    )
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Picking',
        readonly=True,
    )
