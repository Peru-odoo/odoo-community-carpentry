# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

class PlanningMilestone(models.Model):
    """ Is filled-in by end-users on Carpentry Planning, per Launch """ 
    _name = "carpentry.planning.milestone"
    _description = "Planning Milestone"
    _order = "launch_id, column_id, milestone_type_id"

    #===== Fields =====#
    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Project',
        related='launch_id.project_id',
    )
    launch_id = fields.Many2one(
        comodel_name='carpentry.group.launch',
        string='Launch',
        required=True,
        ondelete='cascade'
    )
    milestone_type_id = fields.Many2one(
        comodel_name='carpentry.planning.milestone.type',
        string='Milestone type',
        required=True,
        ondelete='cascade'
    )
    date = fields.Date(
        string='Date',
        default=False
    )

    # related fields
    name = fields.Char(
        related='milestone_type_id.name'
    )
    icon = fields.Char(
        related='milestone_type_id.icon'
    )
    type = fields.Selection(
        related='milestone_type_id.type',
        store=True
    )
    column_id = fields.Many2one(
        related='milestone_type_id.column_id',
        store=True,
    )

    #===== Constrain =====#
    _sql_constraints = [
        ("type_per_column_launch",
        "UNIQUE (launch_id, column_id, type)",
        "This type of milestone already exists on this launch and column."
    )]

    @api.constrains('date', 'milestone_type_id', 'launch_id')
    def _start_end_constraint(self):
        if self._context.get('planning_milestone_no_start_end_constrain'):
            return

        self = self.filtered(lambda x: x.milestone_type_id.type in ['start', 'end'])
        mapped_dates = {
            (x.launch_id.id, x.column_id.id, x.type): x.date
            for x in self.launch_id.milestone_ids
        }
        
        for x in self:
            start_date = mapped_dates.get((x.launch_id.id, x.column_id.id, 'start'))
            end_date = mapped_dates.get((x.launch_id.id, x.column_id.id, 'end'))

            if not start_date or not end_date:
                continue

            if end_date < start_date:
                raise exceptions.ValidationError(_('End date must be after the start date.'))

    def _should_shift(self):
        return self.type in ['start', 'end']
