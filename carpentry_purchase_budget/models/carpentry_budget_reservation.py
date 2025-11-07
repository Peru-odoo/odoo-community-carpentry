# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryBudgetReservation(models.Model):
    _inherit = ["carpentry.budget.reservation"]

    purchase_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Purchase Order',
        ondelete='cascade',
    )

    def _get_record_fields(self):
        return super()._get_record_fields() + ['purchase_id']
