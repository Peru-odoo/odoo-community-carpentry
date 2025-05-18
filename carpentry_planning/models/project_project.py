# -*- coding: utf-8 -*-

from odoo import models, fields, _

class Project(models.Model):
    _inherit = ["project.project"]

    def _compute_display_name(self):
        """ Add current week to display_name """
        super()._compute_display_name()
        
        if self._context.get('display_with_week'):
            for project in self:
                project.display_name += _(
                    ' (W%s)', fields.Date.context_today(self).isocalendar()[1]
                )

    def get_planning_dashboard_data(self):
        """ To be overritten to add Cards in project's top-bar dashboard """
        return {}
    
    #===== Planning Milestones =====#
    planning_milestone_ids = fields.One2many(
        comodel_name='carpentry.planning.milestone',
        inverse_name='project_id',
        string='Planning Milestones',
    )

    def open_planning_milestone_table(self):
        project_id_ = self.id or self.env['project.default.mixin']._get_project_id()
        return {
            'type': 'ir.actions.act_window',
            'name': self.display_name,
            'res_model': self._name,
            'res_id': project_id_,
            'views': [(self.env.ref('carpentry_planning.carpentry_planning_project_milestone_table').id, 'form')],
            'target': 'new',
        }
