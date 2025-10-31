# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command

class Task(models.Model):
    _name = 'project.task'
    _inherit = ['project.task', 'carpentry.budget.mixin']
    _carpentry_budget_notebook_page_xpath = "//page[@id='timesheets_tab']"
    _carpentry_budget_choice = False

    #===== Fields =====#
    allow_timesheets = fields.Boolean(
        # make it user choice per-task instead of per-project
        # False by default, True in specific `Timesheet's budget` task view
        default=False,
        store=True,
        readonly=False
    )
    # budget reservation
    reservation_ids = fields.One2many(domain=[('section_res_model', '=', _name)])
    expense_ids = fields.One2many(domain=[('section_res_model', '=', _name)])
    launch_ids = fields.Many2many(
        string='Launch(s)',
        comodel_name='carpentry.group.launch',
        relation='carpentry_group_launch_task_budget_rel',
        column1='task_id',
        column2='launch_id',
        domain="[('project_id', '=', project_id)]",
        help='For budget & times distribution and follow-up per launch on the planning',
    )
    budget_analytic_ids = fields.Many2many(store=False,)
    budget_unit = fields.Char(default='h')
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
    
    def _get_fields_budget_reservation_refresh(self):
        return super()._get_fields_budget_reservation_refresh() + [
            'analytic_account_id', 'planned_hours', 'allow_timesheets', 'stage_id.fold',
        ]
    
    def _depends_can_reserve_budget(self):
        return ['allow_timesheets']
    def _get_domain_can_reserve_budget(self):
        return [('allow_timesheets', '=', True)]
    def _get_domain_is_temporary_gain(self):
        return [('stage_id.fold', '=', False)]
    
    def _compute_view_fields_totals_one(self, prec, _):
        super()._compute_view_fields_totals_one(prec)
        self.total_budgetable = self.planned_hours

        return self.analytic_account_id.ids
    
    def _get_total_budgetable_by_analytic(self):
        """ [OVERRIDE]
            Auto-budget reservation of tasks is based on `planned_hours`
        """
        return {
            (task.project_id.id, task.analytic_account_id.id):
            task.planned_hours
            for task in self.filtered('analytic_account_id')
        }
    
    #===== Compute budget: date & amounts =====#
    @api.depends('timesheet_ids.date')
    def _compute_date_budget(self):
        rg_result = self.env['account.analytic.line'].read_group(
            domain=[('task_id', 'in', self.ids)],
            groupby=['task_id'],
            fields=['date:max'],
        )
        mapped_data = {x['task_id'][0]: x['date'] for x in rg_result}
        for task in self:
            task.date_budget = mapped_data.get(task.id)
        return super()._compute_date_budget()
