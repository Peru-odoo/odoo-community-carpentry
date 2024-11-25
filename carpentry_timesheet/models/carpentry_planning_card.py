# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class CarpentryPlanningCard(models.Model):
    _inherit = 'carpentry.planning.card'

    task_planned_hours = fields.Float(compute='_compute_task_fields')
    task_remaining_hours = fields.Float(compute='_compute_task_fields')
    task_overtime = fields.Float(compute='_compute_task_fields')
    task_progress = fields.Float(compute='_compute_task_fields')
    task_performance = fields.Float(compute='_compute_task_fields')

    def _compute_task_fields_one(self):
        """ Compute hours performance statistics """
        super()._compute_task_fields_one()

        # sums
        self.task_planned_hours = sum(self.task_ids.mapped('planned_hours'))
        self.task_remaining_hours = sum(self.task_ids.mapped('remaining_hours'))

        # avgs
        hours_done = sum([task.progress * task.planned_hours for task in self.task_ids]) # assessed qty hours done (not consumed)
        self.task_overtime = sum(self.task_ids.mapped('overtime'))
        self.task_progress = bool(self.task_planned_hours) and round(100 * hours_done / self.task_planned_hours, 2)
        self.task_performance = bool(self.task_planned_hours) and round(100 * self.task_overtime / self.task_planned_hours, 2)
    
    def _get_task_fields_list(self):
        return super()._get_task_fields_list() + [
            'task_planned_hours', 'task_remaining_hours',
            'task_overtime', 'task_progress', 'task_performance'
        ]
