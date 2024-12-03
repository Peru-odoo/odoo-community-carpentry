# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.addons.carpentry_planning_task_need.models.project_task import XML_ID_NEED

class CarpentryNeedFamily(models.Model):
    _name = 'carpentry.need.family'
    _inherit = ['project.default.mixin']
    _description = 'Need family'

    #===== Fields methods =====#
    def _get_domain_parent_type_id(self):
        return [
            ('root_type_id', '=', self.env.ref(XML_ID_NEED).id),
            ('task_ok', '=', False)
        ]
    def _get_default_parent_type_id(self):
        """ Return a default `parent_type_id` following user role(s) on
            the project and linked `type_id`, else 1st available
        """
        # Get all elligible `parent_type_id`
        parent_type_ids = self.env['project.type'].search(self._get_domain_parent_type_id())
        
        # Try to filter by roles, else choose 1st available
        role_ids = self.project_id._get_user_role_ids()
        return fields.first(
            parent_type_ids.filtered(lambda x: x.role_id.id in role_ids.ids)
            | parent_type_ids
        )

    #===== Fields =====#
    name = fields.Char(
        string='Need family',
        required=True
    )
    parent_type_id = fields.Many2one(
        # eg. "Need (Method)"
        comodel_name='project.type',
        string='Need Type',
        default=_get_default_parent_type_id,
        domain=_get_domain_parent_type_id,
    )
    need_ids = fields.Many2many(
        comodel_name='carpentry.need',
        relation='carpentry_need_family_rel',
        column1='family_id',
        column2='need_id',
        string='Needs templates',
        domain="[('project_id', '=', project_id), ('parent_type_id', '=', parent_type_id)]",
        required=True
    )
    launch_ids = fields.Many2many(
        comodel_name='carpentry.group.launch',
        relation='carpentry_need_rel_launch',
        column1='need_id',
        column2='launch_id',
        string='Launches',
        domain="[('project_id', '=', project_id)]"
    )
    role_id = fields.Many2one(
        comodel_name='project.role',
        related='parent_type_id.role_id',
    )

    _sql_constraints = [(
        'name_unique',
        'UNIQUE (name, project_id)',
        'A Need Family with this name already exists in the project.'
    )]

    #===== Constrains =====#
    @api.constrains('need_ids')
    def _constrains_need_ids(self):
        """ Unique `type_id.parent_type_id` in same Need Family """
        for family in self:
            if len(family.need_ids.type_id.parent_id.ids) > 1:
                raise exceptions.ValidationError(
                    _('A Need Family cannot mix Needs of different type.')
                )
    
    #====== CRUD =====#
    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        self._reconcile_with_tasks(self.project_id.ids) # after .create()
        return result

    def unlink(self):
        need_ids, project_ids = self.need_ids, self.project_id.ids
        result = super().unlink()
        self._reconcile_with_tasks(project_ids) # reconcile
    
    def write(self, vals):
        result = super().write(vals)
        self._reconcile_with_tasks(self.project_id.ids) # after .write()
        return result

    #===== Logics =====#
    def _reconcile_with_tasks(self, project_ids_):
        """ Assess differences between existing tasks of type 'need' *and* needs in launches (via needs family),
            and create any missing tasks or delete any tasks from removed needs
            
            Copy logic:
             * 1 need translate into 1 task per launch
             * Need Families carry the affectation of needs to launches...
             * 1 need can be affected through several Need Families to same or different
                launches : create only 1 task per launch per need
            => computation must always be done at project level
        """
        # Computation considers archived tasks,
        # (e.g. a generated need we actually don't want on 1 launch)
        self = self.with_context(active_test=False)

        # 1. Define existing & target
        # existing
        domain_task = [
            ('root_type_id', '=', self.env.ref(XML_ID_NEED).id),
            ('project_id', 'in', project_ids_),
            ('need_id', '!=', False) # created automatically from this method before
        ]
        task_ids = self.env['project.task'].search(domain_task)
        existing_tuples = set([
            (fields.first(task.launch_ids), task.need_id) # [0] because tasks of type need have only 1 launch
            for task in task_ids
        ])

        # target
        domain_family = [('project_id', 'in', project_ids_)]
        family_ids = self.env['carpentry.need.family'].search(domain_family)
        target_tuples = set([
            (launch, need)
            for family in family_ids
            for launch in family.launch_ids
            for need in family.need_ids
        ])

        # 2. Delete tasks if a need were removed (only non-converted need)
        to_delete = task_ids.filtered(lambda task: (
            (fields.first(task.launch_ids), task.need_id) in (existing_tuples - target_tuples)
        ))
        to_delete.with_context(force_delete=True).unlink()

        # 3. Create tasks from added need or launch to (a) family(ies)
        self.env['project.task'].sudo().create([
            need._convert_to_task_vals(launch)
            for launch, need in (target_tuples - existing_tuples)
        ])
