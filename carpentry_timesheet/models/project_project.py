# -*- coding: utf-8 -*-

from odoo import models, _

class Project(models.Model):
    _inherit = ['project.project']

    # Timesheets tasks
    def action_open_task_timesheet(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'name': _("Timesheet's follow-up"),
            'views': [
                (self.env.ref('carpentry_timesheet.view_task_kanban_timesheet').id, 'kanban'),
                (False, 'tree'), # native tree view
                (False, 'form'), # 'project.view_task_form2'
            ],
            'domain': [('allow_timesheets', '=', True)],
            'context': {
                'default_allow_timesheets': True,
                'default_planned_hours_required': 1,
                'default_user_ids': [self.env.uid],
                'display_short_name': True, # no code in analytic's display_name
                'display_analytic_budget': True, # show budget in analytic's display_name
            }
        }
