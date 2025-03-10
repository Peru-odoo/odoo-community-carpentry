# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class CarpentryGroupAffectation(models.Model):
    _inherit = ["carpentry.group.affectation"]

    uom_name = fields.Char(
        compute='_compute_uom_name'
    )

    @api.depends('group_id')
    def _compute_uom_name(self):
        for affectation in self:
            affectation.uom_name = 'h' if affectation.group_ref.timesheetable else '€'
