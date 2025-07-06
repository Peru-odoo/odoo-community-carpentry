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
                SUM(available.quantity_affected) AS quantity_affected,
                SUM(available.amount) AS amount,
                SUM(available.subtotal) AS subtotal,
                available.analytic_account_id,
                available.budget_type,

                CASE
                    WHEN available.budget_type IN {tuple(budget_types)}
                    THEN SUM(available.subtotal) * hourly_cost.coef
                    ELSE SUM(available.subtotal)
                END AS value
        """

    def _from(self, model, models):
        return 'FROM carpentry_budget_available AS available'

    def _join(self, model, models):
        return """
            LEFT JOIN carpentry_budget_hourly_cost AS hourly_cost
                ON  hourly_cost.project_id = available.project_id
                AND hourly_cost.analytic_account_id = available.analytic_account_id
        """
    
    def _where(self, model, models):
        return ''
    
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
                hourly_cost.coef
            """
    
    def _orderby(self, model, models):
        return ''
    