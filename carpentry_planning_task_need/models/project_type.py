# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.addons.carpentry_planning_task_need.models.project_task import XML_ID_NEED

class ProjectType(models.Model):
    _inherit = ['project.type']

    column_id = fields.Many2one(
        # required to route tasks between 2 planning's columns
        comodel_name='carpentry.planning.column',
        string='Planning Column',
        ondelete='set null',
    )

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
            column_id.identifier_ref.child_ids.column_id = column_id

