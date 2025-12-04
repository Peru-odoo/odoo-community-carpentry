# -*- coding: utf-8 -*-

from odoo import models, fields, exceptions, _

class Project(models.Model):
    _inherit = ["project.project"]

    #===== Fields =====#
    planning_milestone_ids = fields.One2many(
        comodel_name='carpentry.planning.milestone',
        inverse_name='project_id',
        string='Planning Milestones',
    )

    #===== Planning =====#
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
        return self._get_planning_dashboard_next_projects()
    
    def _get_planning_dashboard_next_projects(self):
        """ Buttons to quickly open the project's planning
            of next Project Manager or Field manager
        """
        assignments = self.assignment_ids.filtered(
            lambda x: x.config_planning_next_project and x.primary
        )
        return {'next_projects': assignments.read(['user_id', 'role_id'])}
    
    def action_open_planning_next_user(self, user_id):
        """
            1. Find all projects where user is assigned with a primary role to show on plannings
            2. and return an action to open only the next one
        """
        # 1.
        domain = [
            ('user_id', '=', user_id),
            ('config_planning_next_project', '=', True),
            ('primary', '=', 'True'),
            ('project_fold', '=', False),
            ('role_id', '!=', False),
            ('project_id', '!=', False),
        ]
        projects = self.env['project.assignment'].search_read(
            domain, ['project_id'], order='project_id ASC'
        )

        # 2.
        next_project_id, start = None, False
        for data in projects:
            project_id = data['project_id'][0]
            if project_id == self.id:
                start = True
            elif start:
                next_project_id = project_id
                break
        
        if next_project_id:
            Wizard = self.env['project.choice.wizard'].with_context(project_id=next_project_id)
            return Wizard.action_choose_project_and_redirect('carpentry_planning.action_open_planning')
        else:
            raise exceptions.UserError(_("No next project for this user."))
    
    #===== Milestones =====#
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
