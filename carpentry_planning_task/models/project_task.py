# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Task(models.Model):
    _name = 'project.task'
    _inherit = ["project.task", "project.default.mixin"]
    _order = 'priority DESC, date_deadline ASC, create_date ASC'

    #===== Fields methods =====#
    @api.model
    def _selection_planning_card_model(self):
        """ Give user the option to link a Planning Card from Task form """
        return [(x.model, x.name) for x in self._get_planning_model_ids()]
    def _get_planning_model_ids(self):
        domain = [('fold', '=', False)]
        column_ids = self.env['carpentry.planning.column'].sudo().search(domain)
        return column_ids.res_model_id
    
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
    card_ref = fields.Reference(
        # user-interface (not stored)
        selection='_selection_planning_card_model',
        string='Planning Card',
        compute='_compute_card_ref',
        inverse='_inverse_card_ref',
        readonly=False,
        ondelete='cascade',
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
    
    #===== Compute & onchange: card_ref =====#
    @api.depends('card_res_model', 'card_res_id')
    def _compute_card_ref(self):
        for task in self:
            is_set = bool(task.card_res_model and task.card_res_id)
            task.card_ref = '%s,%s' % (task.card_res_model, task.card_res_id) if is_set else False
    
    def _inverse_card_ref(self):
        mapped_model_ids = {x.model: x.id for x in self._get_planning_model_ids()}
        for task in self:
            card = task.card_ref
            task.card_res_id = bool(card) and card.id
            task.card_res_model_id = bool(card) and mapped_model_ids.get(card._name)
    
    @api.onchange('card_ref', 'launch_ids')
    def _onchange_card_ref(self):
        """ Automatically link the task to the launches of their planning card """
        for task in self:
            if not task.card_ref:
                continue
            
            # [remove] `card_ref` was changed: remove former launches
            if task._origin.card_ref and task._origin.card_ref != task.card_ref:
                task.launch_ids -= task._origin.card_ref.launch_ids
            
            # [add/keep] launches of `card_ref` if new, keep `card_ref`'s one if `launch_ids` was changed
            task.launch_ids += task.card_ref.launch_ids

    #===== Onchange: link `date_end`, `kanban_state` and `stage_id` =====#
    @api.onchange('date_end')
    def _onchange_date_end(self):
        """ Shortcut: since we display `date_end` in Tree and Form view,
            when user set it, consider the tasks as done
            => update `stage_id` and `kanban_state` accordingly
        """
        res = self._get_stage_open_done()
        for task in self:
            task._change_state_one('date_end', bool(task.date_end), *res)
    
    @api.onchange('kanban_state')
    def _onchange_kanban_state(self):
        """ Shortcut: when user set `kanban_state`, change task
            `stage_id` and `date_end` accordingly
        """
        res = self._get_stage_open_done()
        for task in self:
            has_closed = task._change_state_one('kanban_state', task.kanban_state == 'done', *res)
            if has_closed:
                task.date_end = fields.Date.today()
    
    def _get_stage_open_done(self):
        stage_ids = self.env['project.task.type'].search([])
        stage_open = fields.first(stage_ids.filtered_domain([('fold', '=', False)]))
        stage_done = fields.first(stage_ids.filtered_domain([('fold', '=', True)]))
        return stage_open, stage_done
    
    def _change_state_one(self, field, is_closed, stage_open, stage_done):
        """ Move to Open or Closed stage """
        self.ensure_one()
        has_changed = self._origin[field] != self[field]
        if has_changed:
            if is_closed:
                self.stage_id = stage_done.id
                self.kanban_state = 'done'
            else:
                self.stage_id = stage_open.id
                self.kanban_state = 'normal'
        return has_changed and is_closed
    
    #===== Compute dates: is_late =====#
    @api.depends('date_deadline', 'date_end')
    def _compute_is_late(self):
        for task in self:
            # (i) `date_end` is `datetime` while `date_deadline` is `date`
            date_end_or_today = bool(task.date_end) and task.date_end.date() or fields.Date.today()
            task.is_late = bool(task.date_deadline) and date_end_or_today > task.date_deadline         

    #===== Buttons / action =====#
    def action_open_task_form(self):
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
    
    #===== Task copy =====#
    def _fields_to_copy(self):
        return super()._fields_to_copy() | ['card_res_id', 'card_res_model', 'launch_ids']
    