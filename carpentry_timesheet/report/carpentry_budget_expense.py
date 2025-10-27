# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryExpense(models.Model):
    _inherit = ['carpentry.budget.expense.history']

    #===== View build =====#
    def _get_queries_models(self):
        return super()._get_queries_models() + ('project.task',)
    
    def _select(self, model, models):
        if model == 'project.task':
            return f"""
                SELECT
                    section.project_id,
                    section.date_budget AS date,
                    section.active,
                    section.id AS section_id,
                    {models[model]} AS section_model_id,
                    
                    -- cost center is **ALWAYS** task's one,
                    -- even for employees' timesheets of other departments
                    section.analytic_account_id,
                    analytic.budget_type,

                    -- amount_reserved:
                    -- 1. if effective_hours < amount_reserved:
                    --    displays expense == budget_reservation in the project's budget report
                    --    by cancelling amount_reserved of `carpentry.budget.reservation`
                    -- 2. if planned_hours != amount_reserved:
                    --    fakely raise/reduce amount_reserved by the difference
                    CASE
                        WHEN section.is_closed IS FALSE AND section.effective_hours < SUM(reservation.amount_reserved)
                        THEN section.effective_hours - SUM(reservation.amount_reserved) -- replace `sum(amount_reserved)` by `effective_hours`
                        ELSE 0.0
                    END -
                    CASE
                        WHEN section.planned_hours != SUM(reservation.amount_reserved)
                         AND section.effective_hours < LEAST(SUM(reservation.amount_reserved), section.planned_hours)
                        THEN section.planned_hours - SUM(reservation.amount_reserved)
                        ELSE 0.0
                    END AS amount_reserved,
                    FALSE AS should_devalue_workforce_expense,

                    -- expense
                    SUM(line.unit_amount) AS amount_expense,
                    SUM(line.amount) * -1 AS amount_expense_valued
            """

        return super()._select(model, models)
    
    def _join(self, model, models):
        sql = ''

        if model == 'project.task':
            sql += f"""
                -- timesheet lines
                LEFT JOIN account_analytic_line AS line
                    ON line.task_id = section.id
                
                -- analytic
                LEFT JOIN account_analytic_account AS analytic
                    ON analytic.id = section.analytic_account_id
                
                -- reservation (we need them to calculate the expense conditionnally)
                LEFT JOIN carpentry_budget_reservation AS reservation
                    ON  reservation.section_model_id = {models['project.task']}
                    AND reservation.section_id = section.id
            """
        
        return sql + super()._join(model, models)
    
    def _where(self, model, models):
        """ Override to skip `WHERE budget_type IS NOT NULL`  """
        
        if model == 'project.task':
            return """
                WHERE
                    section.active IS TRUE AND
                    section.allow_timesheets IS TRUE
            """

        return super()._where(model, models)
