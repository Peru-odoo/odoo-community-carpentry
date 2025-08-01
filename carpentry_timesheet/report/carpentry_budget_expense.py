# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryExpense(models.Model):
    """ Should be overriden in each Carpentry module with expense """
    _inherit = ['carpentry.budget.expense.history']

    # fields cancelling
    state = fields.Selection(store=False)

    #===== View build =====#
    def _get_queries_models(self):
        return super()._get_queries_models() + ('project.task',)
    
    def _select(self, model, models):
        return super()._select(model, models) + (
            """
                section.project_id AS project_id,

                -- expense
                -1 * SUM(line.amount) AS amount_expense,
                
                -- gain
                0.0 AS amout_gain,
                CASE
                    WHEN section.effective_hours > section.planned_hours OR section.is_closed
                    THEN TRUE
                    ELSE FALSE
                END AS should_compute_gain,
                FALSE AS should_value_expense
            """ if model == 'project.task' else ''
        )

    def _join(self, model, models):
        sql = ''
        if model == 'project.task':
            sql += """
                INNER JOIN account_analytic_line AS line
                    ON line.task_id = section.id
                
                -- analytic
                LEFT JOIN account_analytic_account AS analytic
                    ON analytic.id = section.analytic_account_id
            """
        
        return sql + super()._join(model, models)
    
    def _where(self, model, models):
        return super()._where(model, models) + (
            """
                AND section.active IS TRUE
                AND section.allow_timesheets IS TRUE
            """
            if model == 'project.task' else ''
        )
    
    def _groupby(self, model, models):
        sql = super()._groupby(model, models)
        
        if model == 'project.task':
            sql += ', section.project_id'
        
        return sql
