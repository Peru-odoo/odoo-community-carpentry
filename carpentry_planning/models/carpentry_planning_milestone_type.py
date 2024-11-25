# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

class PlanningMilestoneType(models.Model):
    """ Settings of milestones list in Carpentry Planning (per column)
        Can be periods (start <-> end) or milestones (type=milestone) """

    _name = "carpentry.planning.milestone.type"
    _description = "Planning Milestone Type"

    #===== Fields =====#
    name = fields.Char(
        string='Name',
        required=True,
        translate=True
    )
    icon = fields.Char(
        string='Icon'
    )
    column_id = fields.Many2one(
        'carpentry.planning.column',
        string='Planning column',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        default=10,
        string='Sequence'
    )
    type = fields.Selection(
        selection=[
            ('start', 'Start'),
            ('end', 'End'),
        ],
        default=False, # False is any kind of date (e.g. a milestone like "Go for purchase")
        required=False
    )

    #===== CRUD =====#
    @api.model_create_multi
    def create(self, vals_list):
        """ Pre-fill planning's launch milestones with empty milestones """
        launch_ids = self.env['carpentry.group.launch'].sudo().search([])
        return super().create(vals_list)._prefill_milestone_ids(launch_ids)
    
    def _prefill_milestone_ids(self, launch_ids):
        self.env['carpentry.planning.milestone'].create([
            {'launch_id': launch.id, 'milestone_type_id': milestone_type.id}
            for launch in launch_ids
            for milestone_type in self
        ])
        return self
