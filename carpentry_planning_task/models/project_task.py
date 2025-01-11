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
    launch_ids = fields.Many2many(
        comodel_name='carpentry.group.launch',
        relation='carpentry_task_rel_launch',
        column1='task_id',
        column2='launch_id',
        string='Launches',
        domain="[('project_id', '=', project_id)]"
    )

    is_late = fields.Boolean(compute='_compute_is_late')
    kanban_state = fields.Selection(compute=False)
    create_date_week = fields.Char(
        string='Create Week',
        compute='_compute_create_date_week'
    )
    date_deadline = fields.Datetime(string='Deadline')
    date_end = fields.Datetime(string='Finish Date')

    #===== Compute `stage_id` depending `date_end` =====#
    @api.depends('date_end')
    def _compute_stage_id(self):
        """ == Overwrite Odoo method ==
            When user set `date_end` consider the tasks as done
        """
        res = self._get_stage_open_done()
        for task in self:
            is_closed = bool(task.date_end)
            has_changed = is_closed != task.is_closed
            task._change_state_one(has_changed, is_closed, *res)
    
    def _get_stage_open_done(self):
        stage_ids = self.env['project.task.type'].search([])
        stage_open = fields.first(stage_ids.filtered_domain([('fold', '=', False)]))
        stage_done = fields.first(stage_ids.filtered_domain([('fold', '=', True)]))
        return stage_open, stage_done
    
    def _change_state_one(self, has_changed, is_closed, stage_open, stage_done):
        """ Move to Open or Closed stage """
        self.ensure_one()
        if has_changed:
            if is_closed:
                self.stage_id = stage_done.id
                self.kanban_state = 'done'
                self.date_end = fields.Datetime.now()
            else:
                self.stage_id = stage_open.id
                self.kanban_state = 'normal'
                self.date_end = False
        return has_changed and is_closed
    
    #===== Compute dates: is_late =====#
    @api.depends('date_deadline', 'date_end')
    def _compute_is_late(self):
        for task in self:
            # (i) `date_end` is `datetime` while `date_deadline` is `date`
            date_end_or_today = bool(task.date_end) and task.date_end.date() or fields.Date.today()
            task.is_late = bool(task.date_deadline) and date_end_or_today.date() > task.date_deadline         

    @api.depends('create_date')
    def _compute_create_date_week(self):
        for task in self:
            date = task.create_date
            task.create_date_week = bool(date) and _('W%s') % str(date.isocalendar()[1])

    #===== Buttons / action =====#
    def button_toggle_done(self):
        self.ensure_one()
        stages = self._get_stage_open_done()
        self._change_state_one(True, not self.is_closed, *stages)
    
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
            else: # Any other models (i.e. a Plan Set, a Task Meeting, ...)
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

    #===== Task copy =====#
    def _fields_to_copy(self):
        return super()._fields_to_copy() | ['card_res_id', 'card_res_model', 'launch_ids']
    