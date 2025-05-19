# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command


class Task(models.Model):
    _name = 'project.task'
    _inherit = ['project.task', 'carpentry.budget.reservation.mixin']

    #===== Fields =====#
    allow_timesheets = fields.Boolean(
        # make it user choice per-task instead of per-project
        # False by default, True in specific `Timesheet's budget` task view
        default=False,
        store=True,
        readonly=False
    )
    # budget reservation
    launch_ids = fields.Many2many(
        string='Launch(s)',
        comodel_name='carpentry.group.launch',
        relation='carpentry_group_launch_task_budget_rel',
        column1='task_id',
        column2='launch_id',
        domain="[('project_id', '=', project_id)]",
        help='For budget & times distribution and follow-up per launch on the planning',
    )
    affectation_ids = fields.One2many(domain=[('section_res_model', '=', _name)])

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


    #====== Affectation / budget reservation ======#
    def _get_budget_types(self):
        return ['service', 'installation']
    
    def _get_fields_affectation_refresh(self):
        return super()._get_fields_affectation_refresh() + ['analytic_account_id', 'planned_hours']

    def _has_real_affectation_matrix_changed(self, _):
        """ Override so that any changes of `planned_hours` updates affectation table """
        return True

    @api.onchange('planned_hours')
    def _set_readonly_affectation(self):
        """ Modifying `planned_hours` re-computes automatically
            the budget matrix after saving the task
        """
        return super()._set_readonly_affectation()
    
    @api.depends('analytic_account_id')
    def _compute_budget_analytic_ids(self):
        """ Budget reservation for task is on the single task's analytic """
        to_compute = self.filtered('project_id')
        if to_compute:
            mapped_analytics = self._get_mapped_project_analytics()

            for task in to_compute:
                task.budget_analytic_ids = (
                    [Command.set([task.analytic_account_id.id])] if
                    task.analytic_account_id.id in mapped_analytics.get(task.project_id.id, [])
                    else False
                )
        
        return super()._compute_budget_analytic_ids()

    def _get_total_by_analytic(self):
        """ :return: Dict like {analytic_id: charged amount} """
        self.ensure_one()
        return {
            task.analytic_account_id.id: task.planned_hours
            for task in self.filtered('analytic_account_id')
        }

    #====== Compute amount ======#
    @api.depends('planned_hours')
    def _compute_amount_budgetable(self):
        for task in self:
            task.amount_budgetable = task.planned_hours

    @api.depends('planned_hours')
    def _compute_amount_gain(self):
        return super()._compute_amount_gain()
