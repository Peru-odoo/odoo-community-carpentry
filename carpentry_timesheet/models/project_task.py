# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.osv import expression

from collections import defaultdict


class Task(models.Model):
    _inherit = ['project.task']

    #===== Fields method =====#
    @api.model
    def _read_group_analytic(self, analytics, domain, order):
        """ Show all timesheetable in column, in task's kanban view """
        domain = ['|', ('id', 'in', analytics.ids), ('timesheetable', '=', True)]
        return analytics.search(domain, order=order, access_rights_uid=SUPERUSER_ID)

    #===== Fields =====#
    analytic_account_id = fields.Many2one(
        domain="""[
            ('timesheetable', '=', True),
            ('budget_line_ids.project_id', 'in', project_id)
            '|', ('company_id', '=', False), ('company_id', '=', company_id),
        ]""",
        group_expand='_read_group_analytic' # for kanban columns
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
        default=False
    )


    #===== Compute =====#
    @api.depends('project_id.allow_timesheets', 'analytic_account_id')
    def _compute_allow_timesheets(self):
        """ Task with no analytic **on the task** (not project) cannot be timesheeted """
        for task in self:
            task.allow_timesheets = task.project_id.allow_timesheets and task.analytic_account_id.id
    
    
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
        elif self.stage_id.fold or self.overtime:
            return 100 * (self.planned_hours - self.effective_hours) / self.planned_hours

        return 0
