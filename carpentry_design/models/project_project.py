# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

class Project(models.Model):
    _inherit = ['project.project']
    
    plan_set_count = fields.Integer(
        string="Plans Sets",
        compute='_compute_plan_set_count'
    )
    
    def _compute_plan_set_count(self):
        rg_result = self.env['carpentry.plan.set'].read_group(
            domain=[('project_id', 'in', self.ids)],
            fields=['plan_set_count:count(id)'],
            groupby=['project_id']
        )
        mapped_count = {x['project_id'][0]: x['plan_set_count'] for x in rg_result}
        for project in self:
            project.plan_set_count = mapped_count.get(project.id, 0)
