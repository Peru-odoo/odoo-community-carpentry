# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.tools import date_utils
from odoo.addons.carpentry_planning.models.carpentry_planning_mixin import PLANNING_CARD_COLOR

XML_ID_NEED = 'carpentry_planning_task_need.task_type_need'

class Task(models.Model):
    _name = "project.task"
    _inherit = ['project.task', 'carpentry.planning.mixin']
    _rec_name = "display_name"

    #===== Fields's methods =====#
    def _filter_needs(self, only_populated=False):
        """ From a task recordset, return only the needs

            :option only_populated: to filter needs manually created from 'Adjust' menu
        """
        return (
            self.filtered('need_id') if only_populated
            else self.filtered(lambda x: x.root_type_id.id == self.env.ref(XML_ID_NEED).id)
        )

    #===== Fields =====#
    # card_res_id = fields.Many2oneReference(
    #     compute='_compute_card_res_id',
    #     store=True,
    #     readonly=False
    # )
    # card_res_model_id = fields.Many2one(
    #     compute='_compute_card_res_id',
    #     store=True,
    #     readonly=False
    # )
    need_id = fields.Many2one(
        comodel_name='carpentry.need',
        string='Need template',
        ondelete='cascade'
    )
    date_deadline = fields.Date(
        compute='_compute_date_deadline',
        store=True,
        readonly=False
    )
    type_name = fields.Char(
        related='type_id.name'
    )
    week_deadline = fields.Integer(
        compute='_compute_week_deadline',
    )
    deadline_week_offset = fields.Integer(
        related='need_id.deadline_week_offset', 
    )
    #--- planning ---
    column_id = fields.Many2one(
        # `column_id` must be stored here because used in SQL view
        # of Carpentry Planning to route tasks between the right columns
        # depending on their `project.type`
        comodel_name='carpentry.planning.column',
        string='Planning Column',
        related='type_id.column_id',
        store=True,
        ondelete='set null',
        recursive=True
    )
    launch_ids = fields.One2many(
        comodel_name='carpentry.group.launch',
        string='Launches',
        compute='_compute_launch_ids',
        search='_search_launch_ids',
    )

    #===== Constrains =====#
    @api.ondelete(at_uninstall=False)
    def _unlink_except_converted(self):
        """ Can't delete a Task of `type=need` if not converted to manual deadline """
        if self._context.get('force_delete'):
            return
        
        if self._filter_needs(only_populated=True).ids:
            raise exceptions.ValidationError(
                _("A Task of type 'Need' cannot be removed. To hide it, archive it."
                  " To really delete it, remove it Needs menu.")
            )

    @api.constrains('type_id')
    def _constrain_no_change_type_id(self):
        """ Cannot change `type_id` for Task of `type=need` """
        needs = self.exists()._filter_needs()
        if needs.filtered(lambda self: self.type_id != self._origin.type_id):
            raise exceptions.ValidationError(
                _("Cannot change a Need Category of the Task once it is created.")
            )

    #===== Compute =====#
    @api.depends('launch_id')
    def _compute_launch_ids(self):
        for task in self:
            task.launch_ids = task.launch_id
    def _search_launch_ids(self, operator, value):
        return [('launch_id', operator, value)]
    
    #===== Compute: planning card color =====#
    def _compute_planning_card_color_class(self):
        for task in self:
            task.planning_card_color_class = task._get_task_state_color()

    def _get_task_state_color(self):
        """ 1. If task is done
                (a) 'success' if satisfied on time -> displayed week: last done's date
                (b) 'warning' elsewise
            2. If task is still to statisfy (in progress) -> displayed week: first to-come deadline
                (c) 'danger' if taskis  overdue
                (d) 'muted' elsewise
        """
        self.ensure_one()
        if not self.date_deadline:
            return 'muted'
        else:
            if self.is_closed:
                color_warning, color_success = 'warning', 'success'
            else: # 2.
                color_warning, color_success = 'danger', 'muted'
            color = color_warning if self.is_late else color_success
        return color

    def _get_state_planning(self):
        """ [TODO ARNAUD] logique vert/orange/rouge... selon date """

    #===== Compute `res_id` and `res_model_id` ======#
    # @api.depends('type_id', 'need_id')
    # def _compute_card_res_id(self):
    #     model_id_ = self.env['ir.model'].sudo()._get('project.type').id
    #     for task in self._filter_needs():
    #         task.card_res_id = task.type_id.id
    #         task.card_res_model_id = model_id_

    #===== Compute `name_required`, `task type` & `launch_id` ======#
    def _get_name_required_type_list(self):
        return super()._get_name_required_type_list() + [self.env.ref(XML_ID_NEED).id]

    #===== Compute date_deadline =====#
    @api.depends(
        'type_id', 'deadline_week_offset',
        'launch_id', 'launch_id.milestone_ids', 'launch_id.milestone_ids.date'
    )
    def _compute_date_deadline(self):
        """ Compute `date_deadline = launch_id."date_[prod/install]_start" - deadline_week_offset` """
        self = self.filtered('deadline_week_offset')
        if not self.ids: # perf optim
            return
        
        # Get milestones date
        domain = [
            ('launch_id', 'in', self.launch_id.ids),
            ('type', '=', 'start')
        ]
        milestone_ids = self.env['carpentry.planning.milestone'].sudo().search(domain)
        mapped_date_start = {}
        for milestone in milestone_ids:
            key = (milestone.launch_id.id, milestone.column_id.id)

            # objective date is the start date of another column
            column_date = milestone.column_id.column_id_need_date
            if column_date:
                domain = [('launch_id', '=', milestone.launch_id.id), ('column_id', '=', column_date.id)]
                milestone = milestone_ids.filtered_domain(domain)

            mapped_date_start[key] = milestone.date

        # Compute `date_deadline`
        for task in self:
            key = (
                task.launch_id.id, # only 1 launch allowed for task of type need
                task.column_id.column_id_need_date.id or task.column_id.id
            )
            date_start = mapped_date_start.get(key) # start date of Production or Installation

            task.date_deadline = bool(date_start) and (
                date_utils.subtract(
                    date_start,
                    weeks = task.deadline_week_offset
                )
            )
    
    @api.depends('date_deadline')
    def _compute_week_deadline(self):
        for task in self:
            task.week_deadline = bool(task.date_deadline) and task.date_deadline.isocalendar()[1]

    #===== Task copy =====#
    def _fields_to_copy(self):
        return super()._fields_to_copy() | ['type_id', 'need_id']

    #===== Planning =====#
    def action_plan_need(self):
        self.write({
            'active': True,
            'stage_id': self._get_default_stage_id().id,
        })

    def action_open_planning_tree(self, domain=[], context={}, record_id=False, project_id_=False):
        """ Called from planning cards
            For need, add additional `default_xx` keys and context
        """

        if record_id and record_id.res_model == 'project.task':
            context |= {
                'default_parent_type_id': self.env.ref(XML_ID_NEED).id,
                'default_type_id': record_id.res_id, # card is the need category
                'display_with_prefix': 1,
                'display_standard_form': False
            }
        return super().action_open_planning_tree(domain, context, record_id, project_id_)

    @api.model
    def _get_planning_subheaders(self, column_id, launch_id):
        """ No deadlines nor budgets in Need columns headers """
        return {}
    