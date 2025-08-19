# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.addons.carpentry_planning_task_need.models.project_task import XML_ID_NEED

class CarpentryNeed(models.Model):
    _name = 'carpentry.need'
    _description = 'Need'
    _order = "deadline_week_offset DESC"

    #===== Fields =====#
    project_id = fields.Many2one(
        related='family_ids.project_id',
        store=True,
        index='btree_not_null'
    )
    name = fields.Char(
        string='Need',
        required=True
    )
    user_ids = fields.Many2many(
        comodel_name='res.users',
        string='Users',
    )
    deadline_week_offset = fields.Integer(
        string='Weeks offset',
        default=1,
        required=True,
        help="Number of week before a given milestone of the launch (e.g. start of Production or Installation)"
    )
    parent_type_id = fields.Many2one(
        # for UX: to filter `type_id` options
        # example: "Need (Method)"
        comodel_name='project.type',
        string='Type of Need',
        compute='_compute_parent_type_id',
        search='_search_parent_type_id',
        domain=lambda self: self.env['carpentry.need.family']._get_domain_parent_type_id(),
    )
    type_id = fields.Many2one(
        comodel_name='project.type',
        string='Need Category',
        required=True,
        ondelete='restrict',
        index='btree_not_null',
        domain="[('parent_id', '=', parent_type_id)]"
    )
    family_ids = fields.Many2many(
        comodel_name='carpentry.need.family',
        relation='carpentry_need_family_rel',
        column1='need_id',
        column2='family_id',
        string='Needs Families'
    )
    task_ids = fields.One2many(
        comodel_name='project.task',
        inverse_name='need_id',
        string='Tasks'
    )


    #===== Constraint =====#
    _sql_constraints = [(
        "name_unique",
        "UNIQUE (name, project_id)",
        "This Need's name already exist in the project."
    )]

    @api.ondelete(at_uninstall=False)
    def _unlink_except_affected(self):
        if any(need.family_ids.ids for need in self):
            raise exceptions.ValidationError(
                _("This need cannot be deleted since used in a Need Family.")
            )
    
    #===== CRUD =====#
    def write(self, vals):
        self._synch_needs_users_to_tasks(vals.get('user_ids'))
        return super().write(vals)
    
    def _synch_needs_users_to_tasks(self, new_user_ids):
        """ Synchronize need's users to task's user,
            for tasks still aligned with their needs
        """
        if not new_user_ids:
            return
        
        for need in self:
            for task in need.task_ids:
                if task.user_ids == need.user_ids:
                    task.user_ids = new_user_ids

    #===== Compute =====#
    @api.depends_context('default_parent_type_id')
    @api.depends('type_id.parent_id')
    def _compute_parent_type_id(self):
        """ Either coming from planning (ctx: `default_parent_type_id`)
            or need family
        """
        default = self._context.get('default_parent_type_id')
        for need in self:
            need.parent_type_id = default or need.type_id.parent_id
    
    @api.model
    def _search_parent_type_id(self, operator, value):
        return [('type_id.parent_id', operator, value)]

    #===== Business methods =====#
    def _convert_need_to_task_vals(self, launch):
        """ Note: by default, Task of type `need` are idle (cf. `stage_id`),
            and planned manually by the project manager in the planning page
        """
        self.ensure_one()
        Task = self.env['project.task']
        return {
            'project_id': self.project_id.id,
            'name': self.name,
            'type_id': self.type_id.id, # need category
            'need_id': self.id,
            'user_ids': self.user_ids.ids,
            'launch_ids': launch.ids,
            'stage_id': Task._get_stage_id_default_need().id,
        }
