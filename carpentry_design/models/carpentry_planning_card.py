# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.osv import expression

class CarpentryPlanningCard(models.Model):
    """ Add required field for specific Plan Releases cards """
    _inherit = ["carpentry.planning.card"]

    plan_release_id = fields.Many2one(
        # for research by launches
        comodel_name='carpentry.plan.release',
        string='Plan Release'
    )

    plan_set_name = fields.Char(compute='_compute_fields')
    week_publish = fields.Integer(compute='_compute_fields')
    week_visa_feedback = fields.Integer(compute='_compute_fields')
    
    def _get_fields(self):
        return super()._get_fields() + ['plan_set_name', 'week_publish', 'week_visa_feedback']
