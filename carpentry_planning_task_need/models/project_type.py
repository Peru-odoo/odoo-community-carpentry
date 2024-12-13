# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.addons.carpentry_planning_task_need.models.project_task import XML_ID_NEED

class ProjectType(models.Model):
    _name = 'project.type'
    _inherit = ['project.type', 'carpentry.planning.mixin']

    #===== Fields (planning) =====#
    column_id = fields.Many2one(
        # required since 2 planning's columns uses `project.type`
        comodel_name='carpentry.planning.column',
        string='Planning Column',
        compute='_compute_column_id',
        store=True,
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
    @api.model
    def _synch_mirroring_column_id(self, column_id):
        """ Called by `carpentry.planning.column` on changes on `identifier_ref`
            This method applies to all records of `project.type` independently of
             arg `column_id`
        """
        # Unset previous
        self.sudo().search([('column_id', '=', column_id.id)]).column_id = False
        
        # Set new
        if column_id.identifier_ref:
            column_id.identifier_ref.column_id = column_id

        
    identifier_res_id = fields.Many2oneReference(
        model_field='identifier_res_model',
        string='Identifier ID',
    )
    identifier_res_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Identifier Model ID',
        ondelete='cascade'
    )
    identifier_res_model = fields.Char(
        string='Identifier Model',
        related='identifier_res_model_id.model',
    )
    
    @api.model
    def _get_planning_subheaders(self, column_id, launch_id):
        """ No deadlines nor budgets in Need columns headers """
        return {}
