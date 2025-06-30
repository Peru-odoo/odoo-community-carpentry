# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryBudgetAvailable(models.Model):
    """ Adds `value` fields to a *new* view just like `carpentry.budget.available`
        following the logics of method `account.analytic.account`.`_value_workforce()`
        from module `project_budget_workforce`

        Meaning: it values (h) to (€) on project's lifetime
    """
    _name = 'carpentry.budget.available.valued'
    _inherit = ['carpentry.budget.available']
    _description = 'Project & launches budgets (valued)'
    _auto = False
    
    #===== Fields =====#
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='project_id.currency_id',
        readonly=True,
    )
    value = fields.Monetary(
        string='Value',
        readonly=True,
    )

    #===== View build =====#
    def _get_queries_models(self):
        return ('carpentry.budget.available',)
    
    def _select(self, model, models):
        budget_types = self.env['account.analytic.account']._get_budget_type_workforce()
        return f"""
            SELECT
                available.unique_key,
                available.project_id,
                available.phase_id,
                available.launch_id,
                available.group_model_id,
                available.position_id,
                SUM(available.quantity_affected) / COUNT(*) AS quantity_affected,
                SUM(available.amount) / COUNT(*) AS amount,
                SUM(available.subtotal) / COUNT(*) AS subtotal,
                available.analytic_account_id,
                available.budget_type,

                CASE
                    WHEN available.budget_type NOT IN {tuple(budget_types)}
                    THEN SUM(available.subtotal)
                    ELSE CASE
                        WHEN (
                            project.date IS NULL OR project.date_start IS NULL
                            OR project.date = project.date_start
                        )
                        THEN 0.0
                        -- valuation computation
                        ELSE SUM(
                            (
                                (
                                    LEAST(project.date, COALESCE(history.date_to, project.date)) -- overlap_end
                                    - GREATEST(project.date_start, history.starting_date) -- overlap_start
                                    + 1.0
                                ) -- overlap_days
                                /
                                (project.date - project.date_start + 1.0) -- total_days
                            ) -- weight_of_period
                            * available.subtotal * history.hourly_cost
                        )
                    END
                END / COUNT(*) AS value
        """

    def _from(self, model, models):
        return 'FROM carpentry_budget_available AS available'

    def _join(self, model, models):
        return """
            INNER JOIN project_project AS project
                ON project.id = available.project_id
            LEFT JOIN hr_employee_timesheet_cost_history AS history
                ON history.analytic_account_id = available.analytic_account_id
        """
    
    def _where(self, model, models):
        budget_types = self.env['account.analytic.account']._get_budget_type_workforce()
        return f"""
            WHERE
                available.budget_type NOT IN {tuple(budget_types)} OR
                project.date_start IS NULL OR project.date IS NULL OR (
                    history.starting_date IS NOT NULL AND (
                        history.starting_date BETWEEN project.date_start AND project.date OR
                        history.date_to       BETWEEN project.date_start AND project.date
                    )
                )
            """
    
    def _groupby(self, model, models):
        return """
            GROUP BY
                available.unique_key,
                available.project_id,
                available.phase_id,
                available.launch_id,
                available.group_model_id,
                available.position_id,
                available.analytic_account_id,
                available.budget_type,
                project.date,
                project.date_start
            """
    
    def _orderby(self, model, models):
        return ''
    