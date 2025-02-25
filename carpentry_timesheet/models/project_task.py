# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.osv import expression

from collections import defaultdict


class Task(models.Model):
    _inherit = ['project.task']

    #===== Fields =====#
    is_timeoff_task = fields.Boolean(
        default=False,
        # compatibility with bridge module `project_timesheet_holidays`.
        # This field is used to prevent timesheeting on tasks that should be timesheeted
        #  from HR Holidays (leaves) application
    )
    allow_timesheets = fields.Boolean(
        # make it user choice per-task instead of per-project
        # False by default, True in specific `Timesheet's budget` task view
        default=False,
        store=True,
        readonly=False
    )

    # -- Planning --
    progress_reviewed = fields.Float(
        string='Reviewed Progress',
        compute='_compute_progress_reviewed_performance'
    )
    performance = fields.Float(
        string='Performance (%)',
        compute='_compute_progress_reviewed_performance',
    )

    # -- UI adjustements --
    user_ids = fields.Many2many(
        help='Only Assignees can log timesheets on the Tasks'
    )
    planned_hours = fields.Float(
        # for Kanban progressbar
        group_operator='sum'
    )
    planned_hours_required = fields.Boolean(
        string='Planned Hours mandatory',
        default=False
    )

    #===== Compute =====#
    @api.depends('project_id.allow_timesheets')
    def _compute_allow_timesheets(self):
        """ If project does not allow timesheets, water-falls it to its tasks """
        self.filtered(lambda x: not x.project_id.allow_timesheets).allow_timesheets = False
    

    @api.depends('stage_id', 'progress', 'overtime')
    def _compute_progress_reviewed_performance(self):
        """ * Fakely make `progress_reviewed` to 100% when task is done
            * Computes `performance`
        """
        for task in self:
            task.progress_reviewed = 100.0 if task.stage_id.fold else task.progress
            task.performance = task._get_performance()
    
    def _get_performance(self):
        """ Task performance:
            - If timesheets without budget: -100%
            - If done or overtime: (planned - done) / planned (+ or - allowed)
            - Else neutral (0%)
        """
        self.ensure_one()

        if self.effective_hours and not self.planned_hours:
            return -100
        elif self.planned_hours and (self.stage_id.fold or self.overtime):
            return 100 * (self.planned_hours - self.effective_hours) / self.planned_hours

        return False
