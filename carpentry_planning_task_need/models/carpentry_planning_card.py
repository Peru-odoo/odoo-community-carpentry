# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons.carpentry_planning_task_need.models.project_task import XML_ID_NEED

class CarpentryPlanningCard(models.Model):
    _inherit = ['carpentry.planning.card']

    #===== Actions & Buttons on Planning View =====#
    def action_open_tasks(self):
        action = super().action_open_tasks()

        is_need = self.res_model == 'project.type'
        launch_id = self._context.get('launch_id')

        if is_need:
            action['context'] = action['context'] | {
                # default
                'default_parent_type_id': self.env.ref(XML_ID_NEED).id,
                'default_type_id': self.res_id, # card is the need category
                'display_with_prefix': False,
                'default_user_ids': [],
                'default_type_deadline': 'computed',
                # user-interface
                'show_launch_ids': 1
            }
        return action
