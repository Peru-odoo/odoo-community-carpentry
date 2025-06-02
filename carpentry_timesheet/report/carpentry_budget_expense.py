# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryExpense(models.Model):
    """ Should be overriden in each Carpentry module with expense """
    _inherit = ['carpentry.budget.expense']

    # fields cancelling
    state = fields.Selection(store=False)

    #===== View build =====#
    def _get_queries_models(self):
        return super()._get_queries_models() + ('project.task',)
    
    def _select(self, model, models):
        return super()._select(model, models) + ("""
            section.effective_hours AS amount_expense,
            CASE
                WHEN section.effective_hours > section.planned_hours OR section.is_closed
                THEN TRUE
                ELSE FALSE
            END AS should_compute_gain
            """ if model == 'project.task' else ''
        )

    def _join(self, model, models):
        return (
            """
                -- analytic
                LEFT JOIN account_analytic_account AS analytic
                ON analytic.id = section.analytic_account_id
            """
            if model == 'project.task'
            else super()._join(model, models)
        )
    
    def _where(self, model, models):
        return super()._where(model, models) + (
            """
                AND section.active IS TRUE
                AND section.allow_timesheets IS TRUE
            """
            if model == 'project.task' else ''
        )
