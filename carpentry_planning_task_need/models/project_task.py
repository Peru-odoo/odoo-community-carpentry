# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.tools import date_utils

XML_ID_NEED = 'carpentry_planning_task_need.task_type_need'

class Task(models.Model):
    _inherit = ["project.task"]
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
    card_res_id = fields.Many2oneReference(
        compute='_compute_card_res_id',
        store=True,
        readonly=False
    )
    card_res_model_id = fields.Many2one(
        compute='_compute_card_res_id',
        store=True,
        readonly=False
    )
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
    type_deadline = fields.Selection(
        selection=[
            ('manual', 'Manual'),
            ('computed', 'Auto'),
        ],
        default='manual'
    )
    deadline_week_offset = fields.Integer(
        related='need_id.deadline_week_offset', 
        store=True
    )
    launch_id = fields.Many2one(
        comodel_name='carpentry.group.launch',
        compute='_compute_launch_id',
        inverse='_inverse_launch_id',
        required=True,
        domain="[('project_id', '=', project_id)]"
    )

    #===== Constrains =====#
    @api.ondelete(at_uninstall=False)
    def _unlink_except_converted(self):
        """ Can't delete a Task of `type=need` if not converted to manual deadline """
        if self._context.get('force_delete'):
            return
        
        if self._filter_needs(only_populated=True).ids:
            raise exceptions.ValidationError(
                _("A Task of type 'Need' which computed deadline cannot be"
                  " deleted. Archive it instead or unaffect the Need Family"
                  " from the Launch.")
            )

    @api.depends('type_id')
    def _constrain_no_change_type_id(self):
        """ Cannot change `type_id` for Task of `type=need` """
        if self._filter_needs().ids:
            raise exceptions.ValidationError(
                _("Cannot change a Need Category of the Task once it is created.")
            )

    @api.depends('type_id', 'launch_ids')
    def _constrain_single_launch_ids(self):
        """ Task of `type=need` are affected to a single launch only """
        for task in self._filter_needs():
            if len(task.launch_ids.ids) != 1:
                raise exceptions.ValidationError(
                    _("Tasks of type 'Need' can be affected to a single launch only.")
                )

    #===== Compute `res_id` and `res_model_id` ======#
    @api.depends('type_id', 'need_id')
    def _compute_card_res_id(self):
        model_id_ = self.env['ir.model'].sudo()._get('project.type').id
        for task in self._filter_needs():
            task.card_res_id = task.type_id.id
            task.card_res_model_id = model_id_

    #===== Compute `name_required`, `task type` & `launch_id` ======#
    def _get_name_required_type_list(self):
        return super()._get_name_required_type_list() + [self.env.ref(XML_ID_NEED).id]

    def _compute_launch_id(self):
        for task in self:
            task.launch_id = fields.first(task.launch_ids)
    def _inverse_launch_id(self):
        for task in self:
            task.launch_ids = [Command.set(task.launch_id.ids)]

    #===== Compute & onchange: user_ids, deadline =====#
    @api.onchange('user_ids')
    def _onchange_user_ids(self):
        """ When a task of type `Need` is assigned to user, make the deadline writable """
        for task in self._filter_needs():
            task.type_deadline = 'manual' if task.user_ids.ids else 'computed'
    
    @api.depends(
        'type_id', 'deadline_week_offset',
        'launch_ids', 'launch_ids.milestone_ids', 'launch_ids.milestone_ids.date'
    )
    def _compute_date_deadline(self):
        """ Compute `date_deadline = launch_ids."date_[prod/install]_start" - deadline_week_offset` """
        self = self._filter_needs()
        if not self.ids: # perf optim
            return
        
        # Get milestones date
        domain = [
            ('launch_id', 'in', self.launch_ids.ids),
            ('type', '=', 'start')
        ]
        milestone_ids = self.env['carpentry.planning.milestone'].sudo().search(domain)
        mapped_date_start = {
            (x.launch_id.id, x.column_id.id):
            x.column_id.column_id_need_date.date if x.column_id.column_id_need_date.id else x.date
            for x in milestone_ids
        }

        # Compute `date_deadline`
        for task in self:
            key = (
                task.launch_id.id, # only 1 launch allowed for task of type need
                task.type_id.column_id.column_id_need_date.id or task.type_id.column_id.id
            )
            date_start = mapped_date_start.get(key) # start date of Production or Installation

            task.date_deadline = bool(date_start) and (
                date_utils.subtract(
                    date_start,
                    weeks = task.deadline_week_offset
                )
            )

    #===== Task copy =====#
    def _fields_to_copy(self):
        return super()._fields_to_copy() | ['type_id', 'need_id']

    #===== Actions & Buttons on Planning View =====#
    def action_open_planning_tree(self, domain=[], context={}, record_id=False, project_id_=False):
        """ Called from planning cards
            For need, add additional `default_xx` keys and context
        """

        if record_id and record_id.id and record_id._name == 'project.type':
            context |= {
                'default_parent_type_id': self.env.ref(XML_ID_NEED).id,
                'default_type_id': record_id.res_id, # card is the need category
                'default_user_ids': [],
                'default_type_deadline': 'computed',
                'display_with_prefix': 1,
                'display_standard_form': False
            }
        return super().action_open_planning_tree(domain, context, record_id, project_id_)
