# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.osv import expression

from odoo.tools.float_utils import float_compare, float_is_zero


class ProjectTaskType(models.Model): # stage (kanban columns)
    _inherit = 'project.task.type'

    # timesheet
    product_id = fields.Many2one('product.template', string='Default Product', domain=[('is_timesheetable', '=', True)],
        help='Optional. Default Product set on Task of this Stage.', ondelete='set null')


class Task(models.Model):
    _inherit = "project.task"

    #===== Fields methods =====#
    @api.model
    def _read_group_product_id(self, records, domain, order):
        employee_product_id = self.env.user.employee_id.product_id
        return employee_product_id if employee_product_id.id and not self.env.user.has_group('project.group_project_manager') else \
            self.env['product.template'].search([('is_timesheetable', '=', True)])
    def _read_group_stage_ids_domain_add(self):
        """ For user-role, display columns (stage_ids) as per `product_id` """
        employee_product_id = self.env.user.employee_id.product_id
        domain = [('product_id.id', '=', employee_product_id.id)] if employee_product_id.id else [(1, '=', 1)]
        return [] if self.env.user.has_group('project.group_project_manager') else \
            expression.OR([super()._read_group_stage_ids_domain_add(), domain])

    #===== Fields =====#
    user_ids = fields.Many2many(help='Only Assignees can log timesheets on the Tasks')
    planned_hours = fields.Float(string='Budget', tracking=False, group_operator='sum')
    available_budget = fields.Integer(string='Remaining budget (h)', compute='_compute_available_budget', store=True)
    is_planned_hours_required = fields.Boolean(default=lambda self: self._context.get('required_planned_hours'))
    product_id = fields.Many2one('product.template', string='Product',
        compute='_compute_product_id', store=True, ondelete='restrict', recursive=True, readonly=False,
        group_expand='_read_group_product_id',
        domain="[('is_timesheetable', '=', True)]", # if wished to restrict only if budget: ('project_budget_ids.project_id', '=', project_id)
        help="Mandatory for timesheets. Can be manually changed. Set by default: 1. Task's Stage default product"
             " ; 2. Employee's default product ; 3. Parent's task Product, but do not erase if already set.")
    allow_timesheets = fields.Boolean(store=True, readonly=False) # make it user choice per task

    performance = fields.Float(string='Performance', compute='_compute_progress_hours', store=True)

    #===== Constrains =====#
    _sql_constraints = [(
        "hours_need_budget",
        "CHECK (available_budget >= 0.0)",
        "Task budget is exceeding available budget in project for tasks on this product."
    ),(
        "timesheet_need_product",
        "CHECK (allow_timesheets IS NOT TRUE OR product_id IS NOT NULL)",
        "A product must be defined on the task before activating timesheets."
    )]
    
    #===== Compute =====#
    def _get_default_product_id(self):
        return self._context.get('default_product_id') or self.stage_id.product_id or self.env.user.employee_id.product_id.id
    def _get_possible_stage_ids(self, stage_ids, type):
        """ Default `stage_id` on task form: depending on user default `product_id` """
        stage_ids = super()._get_possible_stage_ids(stage_ids, type)
        stage_ids_by_product_id = stage_ids.filtered(lambda stage: stage.product_id.id == self._get_default_product_id())
        return stage_ids_by_product_id if stage_ids_by_product_id.ids else stage_ids
    @api.depends('project_id', 'stage_id', 'ancestor_id', 'ancestor_id.product_id')
    def _compute_product_id(self):
        """ 1. Subtasks herits `product_id` of their ancestor (but don't erase `product_id` if already set)
            2. Set `product_id` as per default one on `stage_id` or `employee_id` """
        for task in self:
            task.product_id = task.ancestor_id.product_id.id or self._get_default_product_id()
    
    @api.depends('product_id')
    def _compute_allow_timesheets(self):
        """ User choice, but default as soon as a `product_id` is choosen """
        for task in self:
            task.allow_timesheets = bool(task.product_id.id)
    
    @api.depends('product_id', 'planned_hours', 'project_id.project_budget_ids.quantity', 'project_id.project_budget_ids.product_id')
    def _compute_available_budget(self):
        budget_ids = self.project_id.project_budget_ids
        task_ids = self.project_id.task_ids
        # budget_ids.read('quantity') # prefetching ?
        # task_ids.read('planned_hours')
        for task in self:
            sibling_ids = (task_ids - task._origin).filtered(
                lambda x: x.project_id.id == task.project_id.id and x.product_id.id == task.product_id.id)
            project_budget = sum(budget_ids.filtered(lambda x: x.product_id.id == task.product_id.id).mapped('quantity'))
            already_planned_hours = sum(sibling_ids.mapped('planned_hours'))
            task.available_budget = project_budget - already_planned_hours - task.planned_hours
    
    @api.depends('kanban_state', 'effective_hours', 'subtask_effective_hours', 'planned_hours')
    def _compute_progress_hours(self):
        """ Mark Progress to 100% if kanban_state == 'done', and compute 'performance in %' """
        for task in self:
            task_total_hours = task.effective_hours + task.subtask_effective_hours
            if task.kanban_state in ['done'] or float_compare(task_total_hours, task.planned_hours, precision_digits=2) >= 0:
                task.progress = 100
                task.overtime = task.planned_hours - task_total_hours
                if float_is_zero(task.planned_hours, precision_digits=2):
                    task.performance = -100
                else:
                    task.performance = round(100.0 * task.overtime / task.planned_hours, 2)
            else:
                task.progress = round(100.0 * task_total_hours / task.planned_hours, 2)
                task.overtime, task.performance = False, False
    
    #===== Business methods =====#
    def _convert_need_to_task(self):
        super()._convert_need_to_task()
        self.allow_timesheets = True

