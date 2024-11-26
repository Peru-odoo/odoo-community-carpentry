# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.tools import date_utils

XML_ID_NEED = 'carpentry_planning_task_need.task_type_need'

class Task(models.Model):
    _inherit = ["project.task"]
    _rec_name = "display_name"

    #===== Fields's methods =====#
    def _filter_needs(self, filter_computed=True):
        """ From a task recordset, return only the needs """
        return self.filtered(lambda x: (
            x.root_type_id.id == self.env.ref(XML_ID_NEED).id
            and (not filter_computed or x.type_deadline == 'computed')
        ))

    #===== Fields =====#
    root_type_need = fields.Many2one(
        # needed for `default_root_type_id` and domain search
        comodel_name='project.type',
        string='Need Type',
        compute='_compute_root_type_need',
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
        default='manual',
        readonly=True,
        help= '- "Classic" means a standard Task;\n'
              '- "Need" means the deadline is computed from planning column'
              ' milestone date. Affecting users will convert it to next status;\n'
              '- "Converted Need" means users were affected, changing the task deadline'
              ' to a fix and editable value.'
    )
    deadline_week_offset = fields.Integer(
        related='need_id.deadline_week_offset', 
        store=True
    )

    #===== Constrains =====#
    @api.ondelete(at_uninstall=False)
    def _unlink_except_converted(self):
        """ Can't delete a Task of `type=need` if not converted to manual deadline """
        if self._context.get('force_delete'):
            return
        
        if self._filter_needs().ids:
            raise exceptions.ValidationError(
                _("A Task of type 'Need' which is not converted to an"
                  " independant Task cannot be delete. Please rather use"
                  " Needs menus to delete the Need, or unaffect the Need"
                  " from the Launch.")
            )

    @api.depends('type_id')
    def _constrain_no_change_type_id(self):
        """ Cannot change `type_id` for Task of `type=need` """
        if self._filter_needs(filter_computed=False).ids:
            raise exceptions.ValidationError(
                _("Cannot change a Need Category once Task is created.")
            )

    @api.depends('launch_ids')
    def _constrain_single_launch_ids(self):
        """ Task of `type=need` are affected to a single launch only """
        for task in self._filter_needs(filter_computed=False):
            if len(task.launch_ids.ids) != 1:
                raise exceptions.ValidationError(
                    _("Tasks of type 'Need' must be affected to a single launch only.")
                )

    #===== Compute task type ======#
    def _compute_root_type_need(self):
        """ Used in domain and context' key for default search filter """
        self.root_type_need = self.env.ref(XML_ID_NEED)

    #===== Compute & onchange: user_ids, deadline =====#
    @api.onchange('user_ids')
    def _onchange_user_ids(self):
        """ When a task of type `Need` is assigned to user, make the deadline writable """
        self._filter_needs().type_deadline = 'manual'
    
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
                fields.first(task.launch_ids).id, # only 1 launch allowed for task of type need
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
