# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

class Project(models.Model):
    _inherit = ["project.project"]
    
    sum_effective_hours = fields.Float(string="Effective hours", compute='_compute_sum_effective_hours')

    def _compute_sum_effective_hours(self):
        """ Sum time spent (effective hours) """
        rg_result = self.env['project.task'].sudo().read_group(
            domain=[('project_id', 'in', self.ids)],
            groupby=['project_id'],
            fields=['effective_hours:sum']
        )
        mapped_data = {x.id: x['effective_hours'] for x in rg_result}
        for project in self:
            project.sum_effective_hours = mapped_data.get(project.id, {}).get('effective_hours', False)

    #===== Carpentry Planning =====#
    def get_planning_dashboard_data(self):
        return super().get_planning_dashboard_data() | self._get_planning_dashboard_timesheet_data()

    def _get_planning_dashboard_timesheet_data(self):
        return {
            # 'total_market': self.total_market,
        }
