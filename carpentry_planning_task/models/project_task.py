# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions, Command
from datetime import timedelta

class Task(models.Model):
    _inherit = ["project.task"]
    _order = 'priority DESC, sequence, date_deadline, create_date'

    #===== Fields (planning) =====#
    card_res_id = fields.Many2oneReference(
        # stored
        model_field='card_res_model',
        string='Planning Card ID',
        index=True
    )
    card_res_model_id = fields.Many2one(
        # stored
        comodel_name='ir.model',
        string='Planning Card Model',
        ondelete='cascade',
    )
    card_res_model = fields.Char(
        # not stored
        string='Planning Card Model Name',
        related='card_res_model_id.model',
    )
    launch_id = fields.Many2one(
        comodel_name='carpentry.group.launch',
        domain="[('project_id', '=', project_id)]"
    )
    is_late = fields.Boolean(compute='_compute_is_late')

    #===== Compute =====#
    @api.depends('date_deadline', 'date_end')
    def _compute_is_late(self):
        for task in self:
            # (i) `date_end` is `datetime` while `date_deadline` is `date`
            date_end_or_today = bool(task.date_end) and task.date_end.date() or fields.Date.today()
            task.is_late = bool(task.date_deadline) and date_end_or_today > task.date_deadline

    #===== Buttons / action =====#
    def action_open_planning_form(self):
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'name': 'Tasks',
            'view_mode': 'form',
            'res_id': self.id,
            'context': self._context,
            'target': 'new' if self._context.get('carpentry_planning') else 'current'
        }
        return action
    
    def action_open_planning_tree(self, domain=[], context={}, record_id=False, project_id_=False):
        """ Opens tasks tree in a new window
            :option domain, context: to customize the action
            :option record_id: opened tree view is filtered on cards related to this record
            :option project_id_: must be provided if not guessable from `record_id`
        """
        # Guess `project_id_` if not given
        if not project_id_ and record_id and 'project_id' in record_id:
            project_id_ = record_id.project_id.id
        
        # Default for `card_res_...`
        if record_id and record_id.id:

            # If `record` is a planning card
            if record_id._name == 'carpentry.planning.card':
                res_id_ = record_id.res_id
                res_model_id_ = record_id.column_id.res_model_id.id
            else: # Any other models (e.g. a Plan Set)
                res_id_ = record_id.id
                res_model_id_ = self.env['ir.model'].sudo()._get(record_id._name).id
                
            domain += [
                ('card_res_id', '=', res_id_),
                ('card_res_model_id', '=', res_model_id_)
            ]
            context |= {
                'default_card_res_id': res_id_,
                'default_card_res_model_id': res_model_id_,
                'default_name': record_id.display_name,
            }
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'tree',
            'name': context.get('default_name', _('Planning Tasks')),
            'domain': [('project_id', '=', project_id_)] + domain,
            'context': {
                # default
                'default_project_id': project_id_,
                'default_date_deadline': fields.Date.today() + timedelta(days=7), # next week
                # other
                'search_default_open_tasks': 1,
                'carpentry_planning': True,
            } | context,
            'target': 'new'
        }
