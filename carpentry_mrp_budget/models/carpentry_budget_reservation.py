# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryBudgetReservation(models.Model):
    _inherit = ["carpentry.budget.reservation"]

    production_id = fields.Many2one(
        comodel_name='mrp.production',
        string='Manufacturing Order',
        ondelete='cascade',
    )
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Picking',
        ondelete='cascade',
    )

    def _get_record_fields(self):
        return super()._get_record_fields() + ['production_id', 'picking_id']
