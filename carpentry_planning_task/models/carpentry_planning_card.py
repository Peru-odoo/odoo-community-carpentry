# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command, exceptions
from odoo.addons.carpentry_planning.models.carpentry_planning_card import PLANNING_CARD_COLOR

class CarpentryPlanningCard(models.Model):
    _inherit = ['carpentry.planning.card']
    _description = 'Planning Card'

    #===== Fields =====#
    # /!\ not computed by ORM, manually called from overwritten `search_read`
    task_ids = fields.One2many(
        comodel_name='project.task',
        compute='_compute_task_ids'
    )
    task_week = fields.Integer(compute='_compute_task_fields')
    task_state = fields.Selection(
        selection=[
            ('muted', 'In progress'),
            ('danger', 'Late Task(s)'),
            ('warning', 'Done, some overdue'),
            ('success', 'Done, all on time'),
        ],
        compute='_compute_task_fields'
    )
    task_state_color = fields.Integer(compute='_compute_task_fields')
    task_count_done = fields.Integer(compute='_compute_task_fields')
    task_count_total = fields.Integer(compute='_compute_task_fields')
    task_min_deadline_open = fields.Date(compute='_compute_task_fields')
    task_max_deadline_done = fields.Date(compute='_compute_task_fields')
    task_is_all_done = fields.Boolean(compute='_compute_task_fields')
    task_has_late = fields.Boolean(compute='_compute_task_fields') # not matter done or not

    #===== ORM overwrite =====#
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        vals_list = super().search_read(domain, fields, offset, limit, order, **read_kwargs)
        return self._search_read_extend_vals_list(domain, vals_list)
    
    @api.model
    def _search_read_extend_vals_list(self, domain, vals_list):
        """ Compute and add *fake* tasks fields into the result. Do it here because computation
            of those fields depends of `launch_ids` in domain's search filter, which is not
            available in ORM's standard `compute_...` methods
        """
        launch_id = self._get_domain_part(domain, 'launch_ids')

        # fake-compute the fields
        card_ids = self.browse([vals['id'] for vals in vals_list])
        card_ids._compute_task_ids(launch_id, should_compute=True)
        card_ids._compute_task_fields(should_compute=True)
        mapped_card_ids = {card.id: card for card in card_ids}

        # append the *fake* fields for tasks (which depend on `launch_id`)
        for vals in vals_list:
            vals |= {
                field: mapped_card_ids.get(vals['id'])[field]
                for field in self._get_task_fields_list()
            }
        
        return vals_list

    #===== Tasks =====#
    def _prevent_compute(self, should_compute=False, fields=[]):
        """ Prevent any computation if *fake* `compute_...` methods
            are called by ORM
        """
        if not should_compute: # block any computation if called by ORM
            for field in fields:
                self[field] = False
        return not should_compute
    
    def _compute_task_ids(self, launch_id=None, should_compute=False): # args are optional because of ORM calls
        """ Not called by ORM, but from custom overritten `search_read`
            Sets `task_ids` per card, depending on active search domain filter `launch_id`
            Indeed, 1 card may have different `task_ids` depending on `launch_id`
        """
        if self._prevent_compute(should_compute, ['task_ids']): # block any computation if called by ORM
            return
        
        rg_result = self.env['project.task'].sudo().read_group(
            domain=[('launch_ids', '=', launch_id)],
            groupby=['card_res_model_id', 'card_res_id'],
            fields=['ids:array_agg(id)'],
            lazy=False
        )
        mapped_task_ids = {(x['card_res_model_id'][0], x['card_res_id']): x['ids'] for x in rg_result}
        for card in self:
            key = (card.column_id.res_model_id.id, card.res_id)
            task_ids_ = mapped_task_ids.get(key, [])
            card.task_ids = [Command.set(task_ids_)]
    
    def _compute_task_fields(self, should_compute=False):
        """ Fields depending on active `launch_id` domain filter on the view
            `self.task_ids` should be computed before calling this method
        """
        if self._prevent_compute(should_compute, self._get_task_fields_list()):
            return
        
        for card in self:
            card._compute_task_fields_one()
    def _get_task_fields_list(self):
        return [
            'task_count_total', 'task_count_done',
            'task_is_all_done', 'task_has_late',
            'task_min_deadline_open', 'task_max_deadline_done',
            'task_state', 'task_state_color', 'planning_card_body_color', 'planning_card_color',
            'task_week'
        ]
    def _compute_task_fields_one(self):
        self.ensure_one()

        # count
        self.task_count_total = len(self.task_ids.ids)
        task_ids_done = self.task_ids.filtered(lambda x: x.kanban_state == 'done')
        self.task_count_done = len(task_ids_done)

        # dates
        self.task_is_all_done = not (self.task_ids - task_ids_done)
        self.task_has_late = self.task_ids.filtered('is_late').ids
        dates_deadline = [date for date in self.task_ids.mapped('date_deadline') if date]
        dates_done = [date for date in task_ids_done.mapped('date_end') if date]
        self.task_min_deadline_open = bool(dates_deadline) and min(dates_deadline)
        self.task_max_deadline_done = bool(dates_done) and max(dates_done)

        # task_state -> state & planning_card_color (if not set)
        self.task_state = self._get_task_state()
        self.task_state_color = PLANNING_CARD_COLOR[self.task_state]
        if not self.planning_card_body_color:
            self.planning_card_body_color = self.task_state
        if not self.planning_card_color:
            self.planning_card_color = self.task_state_color

        # task_week
        displayed_date = self.task_max_deadline_done if self.task_is_all_done else self.task_min_deadline_open
        self.task_week = bool(displayed_date) and displayed_date.isocalendar()[1]

    def _get_task_state(self):
        """ 1. If all tasks satisfied (100% done) -> displayed week: last done's date
                (a) 'success' if all satisfied on time
                (b) 'warning' elsewise.
            2. If some tasks still to statisfy (in progress) -> displayed week: first to-come deadline
                (c) 'danger' if 1 task overdue
                (d) 'muted' elsewise.
        """
        self.ensure_one()
        if not self.task_ids.ids or set(self.task_ids.mapped('date_deadline')) == {False}:
            return 'muted'
        else:
            if self.task_is_all_done:
                color_warning, color_success = 'warning', 'success'
            else: # 2.
                color_warning, color_success = 'danger', 'muted'
            color = color_warning if self.task_has_late else color_success
        return color
    
    #===== Actions & Buttons on Planning View =====#
    def action_open_tasks(self):
        self.ensure_one()

        project_id_ = self.env['project.default.mixin']._get_project_id(self._context, self)
        launch_id_ = self._context.get('launch_id')

        if not launch_id_ or not project_id_:
            raise exceptions.UserError(_(
                'Cannot open a planning card\'s tasks if Project or Launch is missing. Context: %s',
                self._context
            ))
        
        return self.env['project.task'].action_open_planning_tree(
            domain=[('launch_ids', '=', launch_id_)],
            context={'default_launch_ids': [launch_id_]},
            record_id=self,
            project_id_=project_id_
        )
