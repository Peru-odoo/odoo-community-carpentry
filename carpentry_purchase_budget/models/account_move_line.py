# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    project_id = fields.Many2one(
        related='',
        comodel_name='project.project',
        compute='_compute_project_id',
        store=True,
    )

    @api.depends('move_id.project_id', 'analytic_distribution')
    def _compute_project_id(self):
        """ 
            `project_id` is computed from `analytic_distribution` in priority,
            else from `account.move` so that the same invoice may handle several
            project (e.g. internal & a business project)
        """
        data = self.env['project.project'].search_read(fields=['id', 'analytic_account_id'])
        mapped_analytics = {x['analytic_account_id'][0]: x['id'] for x in data}

        for line in self:
            analytic_project = set()
            if line.analytic_distribution:
                analytic_project = set(int(x) for x in line.analytic_distribution.keys()) & set(mapped_analytics.keys())
            
            if len(analytic_project) == 1:
                line.project_id = mapped_analytics.get(next(iter(analytic_project)))
            else:
                line.project_id = line.move_id.project_id.id

    def _prepare_analytic_distribution_line(self, distribution, account_id, distribution_on_each_plan):
        """ Adds `project_id` on analytic lines generated from invoice lines """
        return super()._prepare_analytic_distribution_line(distribution, account_id, distribution_on_each_plan) | {
            'project_id': self.project_id.id
        }
