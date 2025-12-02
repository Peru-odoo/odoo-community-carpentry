# -*- coding: utf-8 -*-

from odoo import models, Command

class AccountMoveLine(models.Model):
    _inherit = ["account.move.line"]

    def _prepare_analytic_lines(self):
        """ Add field `budget_project_ids` so that analytic lines
            are counted in projects budget reports:
        """
        vals_list = super()._prepare_analytic_lines()

        mapped_projects_analytics = self._get_mapped_projects_analytics()
        projects_analytics = self._get_analytics_projects(mapped_projects_analytics)
        project_ids = [
            mapped_projects_analytics[aac_id] for aac_id in projects_analytics
            if aac_id in mapped_projects_analytics
        ]
        if project_ids:
            for vals in vals_list:
                if vals['account_id'] not in projects_analytics:
                    vals['budget_project_ids'] = [Command.set(project_ids)]

        return vals_list
