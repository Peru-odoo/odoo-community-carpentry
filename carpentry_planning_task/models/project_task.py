# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions, Command

from datetime import timedelta

class Task(models.Model):
    _name = 'project.task'
    _inherit = ["project.task", "project.default.mixin"]
    _order = 'priority DESC, date_deadline ASC, create_date ASC'

    #===== Fields methods =====#
    # @api.model
    # def _selection_planning_card_model(self):
    #     """ Give user the option to link a Planning Card from Task form """
    #     return [(x.model, x.name) for x in self._get_planning_model_ids()]
    # def _get_planning_model_ids(self):
    #     domain = [('fold', '=', False)]
    #     column_ids = self.env['carpentry.planning.column'].sudo().search(domain)
    #     return column_ids.res_model_id
    
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
    # card_ref = fields.Reference(
    #     # 2024-12-01 (ALY): removed feature of choosing Card Ref from Task's Form (too UI-complex)
    #     # user-interface (not stored)
    #     selection='_selection_planning_card_model',
    #     string='Planning Card',
    #     compute='_compute_card_ref',
    #     inverse='_inverse_card_ref',
    #     readonly=False,
    #     ondelete='cascade',
    # )
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
    # 2024-12-01 (ALY): removed feature of choosing Card Ref from Task's Form (too UI-complex)
    # @api.depends('card_res_model', 'card_res_id')
    # def _compute_card_ref(self):
    #     for task in self:
    #         is_set = bool(task.card_res_model and task.card_res_id)
    #         task.card_ref = '%s,%s' % (task.card_res_model, task.card_res_id) if is_set else False
    
    # def _inverse_card_ref(self):
    #     mapped_model_ids = {x.model: x.id for x in self._get_planning_model_ids()}
    #     for task in self:
    #         card = task.card_ref
    #         task.card_res_id = bool(card) and card.id
    #         task.card_res_model_id = bool(card) and mapped_model_ids.get(card._name)
    
    # @api.onchange('card_ref', 'launch_ids')
    # def _onchange_card_ref(self):
    #     """ Automatically link the task to the launches of their planning card """
    #     for task in self:
    #         if not task.card_ref:
    #             continue
            
    #         # [remove] `card_ref` was changed: remove former launches
    #         if task._origin.card_ref and task._origin.card_ref != task.card_ref:
    #             task.launch_ids -= task._origin.card_ref.launch_ids
            
    #         # [add/keep] launches of `card_ref` if new, keep `card_ref`'s one if `launch_ids` was changed
    #         task.launch_ids += task.card_ref.launch_ids

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
            task._change_state_one('date_end', has_changed, is_closed, *res)
    
    # Does not work well & actually not wanted
    # @api.onchange('kanban_state')
    # def _onchange_kanban_state(self):
    #     """ Shortcut: when user set `kanban_state`, change task
    #         `stage_id` and `date_end` accordingly
    #     """
    #     res = self._get_stage_open_done()
    #     for task in self:
    #         has_closed = task._change_state_one('kanban_state', task.kanban_state == 'done', *res)
    #         if has_closed:
    #             task.date_end = fields.Date.today()
    
    def _get_stage_open_done(self):
        stage_ids = self.env['project.task.type'].search([])
        stage_open = fields.first(stage_ids.filtered_domain([('fold', '=', False)]))
        stage_done = fields.first(stage_ids.filtered_domain([('fold', '=', True)]))
        return stage_open, stage_done
    
    def _change_state_one(self, field, has_changed, is_closed, stage_open, stage_done):
        """ Move to Open or Closed stage """
        self.ensure_one()
        if has_changed:
            if is_closed:
                self.stage_id = stage_done.id
                # self.kanban_state = 'done'
            else:
                self.stage_id = stage_open.id
                # self.kanban_state = 'normal'
        return has_changed and is_closed
    
    #===== Compute dates: is_late =====#
    @api.depends('date_deadline', 'date_end')
    def _compute_is_late(self):
        for task in self:
            # (i) `date_end` is `datetime` while `date_deadline` is `date`
            date_end_or_today = bool(task.date_end) and task.date_end.date() or fields.Date.today()
            task.is_late = bool(task.date_deadline) and date_end_or_today > task.date_deadline         

    #===== Buttons / action =====#
    def action_open_planning_task_form(self):
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
    
    def action_open_planning_task_tree(self, domain=[], context={}, record_id=False, project_id_=False):
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
            model_id_ = self.env['ir.model']._get(record_id._name).id
            domain += [
                ('card_res_id', '=', record_id.id),
                ('card_res_model_id', '=', model_id_)
            ]
            context |= {
                # 'default_card_ref': '{},{}' . format(record_id._name, record_id.id),
                'default_card_res_id': record_id.id,
                'default_card_res_model_id': model_id_,
                'default_name': record_id.display_name,
            }
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'tree',
            'name': _('Planning Tasks'),
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
    