# -*- coding: utf-8 -*-

from odoo import models, tools, fields
from psycopg2.extensions import AsIs

class CarpentryBudgetHourlyCost(models.Model):
    """ Ratio per project & analytic of hourly costs,
        from `hr_employee_timesheet_cost_history`
    """
    _name = 'carpentry.budget.hourly.cost'
    _description = 'Project hourly costs ratio'
    _auto = False
    
    project_id = fields.Many2one(
        comodel_name='project.project',
        readonly=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        readonly=True,
    )
    budget_type = fields.Selection(
        string='Budget category',
        selection=lambda self: self.env['account.analytic.account'].fields_get()['budget_type']['selection'],
        readonly=True,
    )
    coef = fields.Float(
        readonly=True,
    )

    #===== View build =====#
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        self._cr.execute("""
            CREATE or REPLACE VIEW %s AS (
                %s -- select
                %s -- from
                %s -- join
                %s -- where
                %s -- groupby
                %s -- orderby
            )""", (
                AsIs(self._table),
                AsIs(self._select()),
                AsIs(self._from()),
                AsIs(self._join()),
                AsIs(self._where()),
                AsIs(self._groupby()),
                AsIs(self._orderby()),
            )
        )
    
    def _select(self):
        return f"""
            SELECT
                row_number() OVER (
                    ORDER BY budget_line.project_id, budget_line.analytic_account_id
                ) AS id,
                budget_line.project_id,
                budget_line.analytic_account_id,
                budget_line.budget_type,
                SUM(
                    (
                        (
                            LEAST(project.date, COALESCE(history.date_to, project.date)) -- overlap_end
                            - GREATEST(project.date_start, history.starting_date) -- overlap_start
                            + 1.0
                        ) -- overlap_days
                        /
                        (project.date - project.date_start + 1.0) -- total_days
                    ) -- weight_of_period
                    * history.hourly_cost
                ) / COUNT(*)
                AS coef
        """

    def _from(self):
        return 'FROM account_move_budget_line AS budget_line'

    def _join(self):
        return """
            INNER JOIN project_project AS project
                ON project.id = budget_line.project_id
            INNER JOIN hr_employee_timesheet_cost_history AS history
                ON history.analytic_account_id = budget_line.analytic_account_id
        """
    
    def _where(self):
        budget_types = self.env['account.analytic.account']._get_budget_type_workforce()
        sql_budget_types = "'" + "','" . join(budget_types) + "'"
        return f"""
            WHERE
                budget_line.budget_type IN ({sql_budget_types}) AND
                project.date_start IS NOT NULL AND project.date IS NOT NULL AND (
                    history.starting_date IS NOT NULL AND (
                        history.starting_date   BETWEEN project.date_start AND project.date
                        OR history.date_to      BETWEEN project.date_start AND project.date
                    )
                    OR history.date_to IS NULL AND history.starting_date <= project.date
                )
            """
    
    def _groupby(self):
        return """
            GROUP BY
                budget_line.project_id,
                budget_line.analytic_account_id,
                budget_line.budget_type,
                project.date,
                project.date_start
            """
    
    def _orderby(self):
        return ''
    