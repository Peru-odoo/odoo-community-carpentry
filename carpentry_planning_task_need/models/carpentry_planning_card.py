# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.osv import expression

class CarpentryPlanningCard(models.Model):
    """ Add required field for specific Tasks cards """
    _inherit = ["carpentry.planning.card"]

    project_task_id = fields.Many2one(
        # for research by launches
        comodel_name='project.task',
        string='Task'
    )

    week_deadline = fields.Integer(compute='_compute_fields')
    
    def _get_fields(self):
        return super()._get_fields() + ['week_deadline']

    #===== Button =====#
    def action_plan_need(self):
        task = self.env['project.task'].browse(self.res_id)
        return task.action_plan_need()
