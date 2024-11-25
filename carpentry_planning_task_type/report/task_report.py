# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions
from odoo.addons.carpentry_planning_task_type.models.project_task import XML_ID_INSTRUCTION

class TaskReportProject(models.AbstractModel):
    _name = "report.carpentry_planning_task_type.task_report_project"
    _description = "Task Report Project"

    @api.model
    def _get_report_values(self, docids, data=None):
        return {'docs': self}

class Task(models.Model):
    _inherit = ["project.task"]

    def _get_is_stamp(self):
        return self.env.ref(XML_ID_INSTRUCTION).id in self.mapped('root_type_id')
    
    def _send_email(self):
        """ Called by user, from tree of `project.task`
            We redirect to Send wizard of `project.project` to send only 1 message with 1 attachment
        """

        if len(self.project_id.ids) > 1:
            raise exceptions.UserError(
                _('All documents to send must belong to the same project.')
            )
        action = {
            'name': _('Send %s') % self.root_type_id.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'mail.compose.message',
            'context': {
                'default_composition_mode': 'comment',
                'default_template_id': self.env.ref('carpentry_planning_task_type.task_email_template').id,
                # switch from task to project model the send wizard
                'default_model': 'project.project',
                'default_res_id': self.project_id.id,
                'default_author_id': self.env.user.partner_id.id,
                'default_partner_ids': [self.env.user.partner_id.id],
                # recall the task_ids in context
                'report_task_ids': self.ids,
            }
        }
        return action
