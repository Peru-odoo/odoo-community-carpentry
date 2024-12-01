# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.tools import date_utils
from odoo.osv import expression
from collections import defaultdict

XML_ID_MILESTONE = 'carpentry_planning_task_type.task_type_milestone'
XML_ID_MEETING = 'carpentry_planning_task_type.task_type_meeting'
XML_ID_INSTRUCTION = 'carpentry_planning_task_type.task_type_instruction'

class Task(models.Model):
    """ Manages special tasks: Instructions, Meetings, Milestones """
    _inherit = ['project.task']
    _rec_name = 'display_name'

    #===== Fields' methods =====#
    @api.model
    def default_get(self, field_names):
        defaults_dict = super().default_get(field_names)
        
        # Default `type_id`
        type_id = None
        if 'type_id' in field_names and not self._context.get('default_type_id'):
            type_id = self._get_default_type_id()
            defaults_dict['type_id'] = type_id.id
            defaults_dict['parent_type_id'] = type_id.parent_id.id
        return defaults_dict

    def _get_default_type_id(self):
        """ Set a default `type_id` within the possible allowed
            by `root_type_id` and `parent_type_id`
        """
        # Get possible `type_ids`
        root_type_id = self.root_type_id.id or self._context.get('default_root_type_id')
        domain = [
            ('root_type_id', '=', root_type_id),
            ('task_ok', '=', True),
        ]+([('parent_id', '=', self.parent_type_id.id)] if self.parent_type_id.id else [])
        type_ids = self.env['project.type'].search(domain)

        # If some seems more relevant/compatible with roles of current user
        # auto-suggest this default in preference
        domain_role = [('role_id.assignment_ids.user_id', '=', self.env.uid)]
        filtered_type_ids = type_ids.filtered_domain(domain_role)
        type_ids = filtered_type_ids if filtered_type_ids.ids else type_ids

        return fields.first(type_ids)
    
    @api.model
    def _read_group_types(self, records, domain, order, task_ok=True):
        return self.env['project.type'].search([
            ('task_ok', 'in', records.mapped('task_ok')), # of the same hierarchy level
            ('root_type_id', 'in', records.root_type_id.ids), # in the same type category
        ])


    #===== Fields =====#
    root_type_id = fields.Many2one(
        comodel_name='project.type',
        string='Task Type',
        related='type_id.root_type_id',
        store=True,
        readonly=True
    )
    parent_type_id = fields.Many2one(
        # in N-levels type hierarchy:
        # - `type_id` is the N (last/bottom) --> Need category
        # - `parent_type_id` is the N-1 --> e.g. "Needs (method)"
        # - `root_type_id` is the 1st (top) --> e.g. "Needs"
        comodel_name='project.type',
        string='Parent Category',
        related='type_id.parent_id',
        readonly=True,
        store=True,
        domain="[('root_type_id', '=', root_type_id), ('task_ok', '=', False)]",
        group_expand='_read_group_types'
    )
    type_id = fields.Many2one(
        # from module `project_type`
        string='Category',
        required=True,
        domain="""[
            ('root_type_id', '=', root_type_id),
            ('parent_id', '=', parent_type_id),
            ('task_ok', '=', True)
        ]""",
        group_expand='_read_group_types'
    )
    type_sequence = fields.Integer(
        related='type_id.sequence',
        store=True,
        string='Type Sequence'
    )

    #===== Fields =====#
    # -- Original --
    name = fields.Char(
        required=False
    )
    partner_id = fields.Many2one(
        # `partner_id` is already hidden on view: not relevant for Vertical construction
        # to have it in tasks. Disable also the ORM field, so it is never added to chatter
        default=False,
        tracking=False,
        compute=False,
    )

    # -- Specific --
    # instructions: may have many types
    type_ids = fields.Many2many(
        comodel_name='project.type',
        relation='project_task_subtype_rel',
        string='Categories',
        domain="[('root_type_id', '=', root_type_id), ('task_ok', '=', True)]",
    )
    # meetings
    message_last_date = fields.Date(
        string='Last Message',
        compute='_compute_message_fields'
    )
    count_message_ids = fields.Integer(
        string='Message Count',
        compute='_compute_message_fields'
    )

    # -- User-interface --
    copy_task_id = fields.Many2one(
        # quick overrite, see module `project_task_copy`
        domain="[('project_id', '=', copy_project_id), ('root_type_id', '=', root_type_id)]"
    )
    name_required = fields.Boolean(
        compute='_compute_name_required'
    )

    #===== Constrain =====#
    @api.constrains('root_type_id', 'parent_type_id', 'type_id')
    def _constrain_type_id(self):
        """ Ensure `task.type_id` follow type hierarchy (i.e. is a child of `task.parent_type_id`) """
        for task in self:
            error = (
                task.type_id.parent_id != task.parent_type_id
                or task.type_id.root_type_id != task.root_type_id
            )
            if error:
                raise exceptions.ValidationError(
                    _("Task Category must be in Parent's Category.")
                )


    #===== Compute: user-interface =====#
    @api.depends('root_type_id')
    def _compute_name_required(self):
        """ Required for:
            1. standard Task ; `default_root_type_id = False`
            2. instruction
            3. need (see module `carpentry_planning_task_need`)
        """
        required_list = self._get_name_required_type_list()
        default_root_type_id = self._context.get('default_root_type_id')
        required_by_ctx = not default_root_type_id or default_root_type_id in required_list # for new task, without id yet
        for task in self:
            task.name_required = required_by_ctx or task.root_type_id.id in required_list
    def _get_name_required_type_list(self):
        return [self.env.ref(XML_ID_INSTRUCTION).id]

    #===== Compute: display_name =====#
    @api.depends('name', 'type_id', 'root_type_id')
    def _compute_display_name(self):
        for task in self:
            task.display_name = task._get_prefix_display_name() + (task.name or '')
    
    def _get_prefix_display_name(self):
        """ Add `type_id.name` in front of name, separated by a dash "-",
            only when needed/relevant
        """
        self.ensure_one()
        should_prefix = bool(
            self._context.get('display_with_prefix', True)
            and self._should_display_name_prefix()
        )
        dash = ' - ' if self.type_id.name and self.name else ''

        return (
            '' if not should_prefix or not self.type_id.name
            else self.type_id.name + dash
        )
    
    def _should_display_name_prefix(self):
        """ Classic and Instruction: never prefix the `display_name` """
        no_prefix = [False, self.env.ref(XML_ID_INSTRUCTION)]
        return self.root_type_id not in no_prefix
    
    #===== Onchange: type =====#
    @api.onchange('root_type_id', 'parent_type_id')
    def _onchange_root_parent_type_id(self):
        """ Update pre-select `type_id` to follow its parent """
        for task in self:
            task.type_id = task._get_default_type_id()

    #===== Specific: meetings =====#
    @api.depends('type_id', 'message_ids')
    def _compute_message_fields(self):
        rg_result = self.env['mail.message'].sudo().read_group(
            domain=[('id', 'in', self.message_ids.ids), ('message_type', '=', 'comment')],
            fields=['create_date:max', 'res_id'],
            groupby=['res_id']
        )
        mapped_data = {
            x['res_id']: {'last_date': x['create_date'], 'count': x['res_id_count']}
            for x in rg_result
        }
        for task in self:
            task.message_last_date = mapped_data.get(task.id, {}).get('last_date')
            task.count_message_ids = mapped_data.get(task.id, {}).get('count')

    #===== Action =====#
    def _get_task_views(self, type, custom, switch, module='carpentry_planning_task_type'):
        views = {
            'tree': self.env.ref('project.view_task_tree2').id,
            'form': self.env.ref('project.view_task_form2').id,
            'kanban': self.env.ref('project.view_task_kanban').id,
            'calendar': self.env.ref('project.view_task_calendar').id,
            'timeline': self.env.ref('project_timeline.project_task_timeline').id,
            'activity': self.env.ref('project.project_task_view_activity').id,
        }
        return [((
                views[view_mode] if view_mode not in custom
                else self.env.ref(f'{module}.view_task_{view_mode}_{type}').id
            ), view_mode
        ) for view_mode in switch]

    #===== Buttons / action =====#
    def action_open_planning_task_form(self):
        """ Redirect to task' specific form on tree's button `Details` """
        action = super().action_open_planning_task_form()

        if not self._context.get('display_standard_form'): # stay on standard form for Planning Tasks
            views = self._context.get('action_origin', {}).get('views', {}) # see `project.choice.wizard` for `action_origin`
            views_form = [x[0] for x in views if x[1] == 'form']
            if len(views_form):
                action |= {'view_id': views_form[0]}
        
        return action

    def action_open_planning_task_tree(self, domain=[], context={}, record_id=False, project_id_=False):
        """ For `Create Task` button for Meeting, Instruction...:
            * `record_id` IS the task -> like planning task to Meeting, Instruction ...
            * don't propagate `default_parent_type_id`

            `See carpentry_planning_task` for parent method
        """
        context |= {'display_standard_form': True}
        return super().action_open_planning_task_tree(domain, context, self, self.project_id.id)

    #===== Task copy =====#
    def _fields_to_copy(self):
        return super()._fields_to_copy() | ['attachment_ids']
