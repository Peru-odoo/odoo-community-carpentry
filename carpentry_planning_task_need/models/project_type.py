# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.addons.carpentry_planning_task_need.models.project_task import XML_ID_NEED

class ProjectType(models.Model):
    _name = 'project.type'
    _inherit = ['project.type', 'carpentry.planning.mixin']

    #===== Fields (planning) =====#
    shortname = fields.Char(
        string='Short Name',
        help='Title of planning cards'
    )
    column_id = fields.Many2one(
        # required since 2 planning's columns uses `project.type`
        comodel_name='carpentry.planning.column',
        string='Planning Column',
        compute='_compute_column_id',
        store=True,
        readonly=True,
        required=False,
        ondelete='set null',
        recursive=True
    )
    planning_card_color_is_auto = fields.Boolean(default=True, store=False)
    # don't set field `planning_card_color`, so that Planning Card's color follows `task_state_color`


    #===== Compute =====#
    @api.depends('parent_id', 'parent_id.column_id')
    def _compute_column_id(self):
        """ `column_id` must be stated and stored here because used in SQL view
            of Carpentry Planning to route records of `project.type` between
            the right columns of Carpentry Planning
        """
        for type_id in self:
            type_id.column_id = type_id.parent_id.column_id


    #===== Planning =====#
    def _synch_mirroring_column_id(self, column_id):
        """ Called by `carpentry.planning.column` on changes on `identifier_ref` """
        self.child_ids.column_id = column_id
    
    @api.model
    def _get_planning_subheaders(self, column_id, launch_id):
        """ No deadlines nor budgets in Need columns headers """
        return {}
