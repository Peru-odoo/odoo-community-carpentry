# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.addons.carpentry_planning_task_need.models.project_task import XML_ID_NEED

class CarpentryNeed(models.Model):
    _name = 'carpentry.need'
    _description = 'Need'
    _order = "deadline_week_offset DESC"

    #===== Fields methods =====#
    def _default_parent_type_id(self):
        """ Return a default `parent_type_id` according to user role(s) on the project,
            else 1st one
        """
        domain = [('root_type_id', '=', self.env.ref(XML_ID_NEED).id)]
        parent_type_ids = self.env['project.type'].search(domain)
        
        # current user's role(s) on the project
        role_ids = self.project_id._get_user_role_ids(self.env.user)
        suggestion = parent_type_ids.filtered(lambda x: x.role_id.id in role_ids.ids)

        return fields.first(suggestion) if suggestion.ids else fields.first(parent_type_ids)

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
    deadline_week_offset = fields.Integer(
        string='Weeks offset',
        default=1,
        required=True,
        help="Number of week before a given milestone of the launch (e.g. start of Production or Installation)"
    )
    type_id = fields.Many2one(
        comodel_name='project.type',
        string='Need Category',
        required=True,
        ondelete='restrict',
        index='btree_not_null',
        domain="""[
            ('root_type_id', '=', root_type_need),
            ('parent_id', '=', parent_type_id),
            ('task_ok', '=', True)
        ]"""
    )
    parent_type_id = fields.Many2one(
        # for UX: to filter `type_id` options
        # example: "Need (Method)"
        comodel_name='project.type',
        string='Type of Need',
        domain="[('root_type_id', '=', root_type_need), ('task_ok', '=', False)]",
        default=_default_parent_type_id,
        readonly=False,
        store=False
    )
    root_type_need = fields.Many2one(
        # needed for `default_type_id` and domain search
        comodel_name='project.type',
        string='Need Type',
        default=lambda self: self.env.ref(XML_ID_NEED),
        store=False
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
    
    #===== Business methods =====#
    def _convert_to_task_vals(self, launch_id_, model_id_, stage_id_):
        self.ensure_one()
        return {
            'project_id': self.project_id.id,
            'name': self.name,
            'type_id': self.type_id.id, # need category
            'need_id': self.id,
            'type_deadline': 'computed',
            'user_ids': [Command.clear()],
            'stage_id': stage_id_,
            # planning
            'card_res_model_id': model_id_,
            'card_res_id': self.type_id.id,
            'launch_ids': [Command.set([launch_id_])],
        }
