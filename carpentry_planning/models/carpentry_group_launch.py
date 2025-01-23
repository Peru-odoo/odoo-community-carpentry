# -*- coding: utf-8 -*-

from odoo import models, fields, api

class CarpentryLaunch(models.Model):
    _inherit = ['carpentry.group.launch']

    is_done = fields.Boolean(string='Done?', default=False)
    carpentry_planning = fields.Boolean(compute='_compute_carpentry_planning')
    milestone_ids = fields.One2many(
        comodel_name='carpentry.planning.milestone',
        inverse_name='launch_id',
        string='Milestones'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """ Pre-fill planning's launch milestones with empty milestones """
        launch_ids = super().create(vals_list)
        self.env['carpentry.planning.milestone.type'].sudo().search([])._prefill_milestone_ids(launch_ids)
        return launch_ids

    @api.depends_context('carpentry_planning')
    def _compute_carpentry_planning(self):
        self.carpentry_planning = self._context.get('carpentry_planning')
