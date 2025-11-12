# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from psycopg2.extensions import AsIs

class CarpentryBudgetProject(models.Model):
    """ Final budget report of budget/expense per project """
    _name = 'carpentry.budget.project'
    _inherit = ['carpentry.budget.expense']
    _description = 'Budget project balance'
    _auto = False
    _order = 'project_id, sequence'

    #===== Fields =====#
    sequence = fields.Integer()
    available_valued = fields.Monetary(
        string='Available budget',
        readonly=True,
    )
    percent_gain = fields.Float(
        string='Gain (%)',
        digits=[10,1],
        readonly=True,
        group_operator='avg',
    )
    # cancelled fields
    state = fields.Selection(store=False)
    date = fields.Date(store=False)
    amount_reserved = fields.Float(store=False)
    amount_expense = fields.Monetary(store=False)

    #===== View build =====#
    def _get_queries_models(self):
        """ Inherited in sub-modules (purchase, mrp, timesheet) """
        return ('account.move.budget.line', 'carpentry.budget.expense',)
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        queries = self._get_queries()
        if queries:
            self._cr.execute("""
                CREATE or REPLACE VIEW %(view_name)s AS (
                    
                    %(select)s

                    FROM (
                        (%(union)s)
                    ) AS result
                    
                    INNER JOIN account_analytic_account AS analytic
                        ON analytic.id = result.analytic_account_id

                    %(groupby)s
                
                )""", {
                    'select':    AsIs(self._view_select()),
                    'groupby':   AsIs(self._view_groupby()),
                    'view_name': AsIs(self._table),
                    'union':     AsIs(') UNION ALL (' . join(queries)),
            })
    
    #===== View definition =====#
    def _view_select(self):
        return """
            SELECT
                row_number() OVER (ORDER BY
                    project_id,
                    analytic_account_id
                ) AS id,
                
                project_id,
                result.budget_type,
                analytic_account_id,
                sequence,
                result.active,
                
                record_id AS record_id,
                record_model_id,
                
                SUM(available_valued) AS available_valued,
                SUM(amount_reserved) AS amount_reserved,
                SUM(amount_reserved_valued) AS amount_reserved_valued,
                SUM(amount_expense) AS amount_expense,
                SUM(amount_expense_valued) AS amount_expense_valued,
                SUM(amount_gain) AS amount_gain,
                CASE
                    WHEN SUM(amount_reserved_valued) != 0
                    THEN SUM(amount_gain) / SUM(amount_reserved_valued) * 100.0 
                    ELSE 0.0
                END AS percent_gain
        """
    
    def _view_groupby(self):
        return """
            GROUP BY
                project_id,
                result.budget_type,
                analytic_account_id,
                record_id,
                record_model_id,
                sequence,
                result.active
        """
    
    
    #===== Union sub-queries definition =====#
    def _select(self, model, models):
        if model == 'account.move.budget.line':
            return f"""
                SELECT 
                    'budget' AS state,

                    project_id,
                    budget_type,
                    analytic_account_id,
                    id AS record_id,
                    {models['account.move.budget.line']} AS record_model_id,
                    TRUE AS active,

                    balance AS available_valued, -- always valued
                    0.0 AS amount_reserved,
                    0.0 AS amount_reserved_valued,
                    0.0 AS amount_expense,
                    0.0 AS amount_expense_valued,
                    0.0 AS amount_gain
            """
        else:
            return """
                SELECT
                    'expense' AS state,

                    project_id,
                    budget_type,
                    analytic_account_id,
                    record_id,
                    record_model_id,
                    active,

                    0.0 AS available_valued,
                    amount_reserved,
                    amount_reserved_valued,
                    amount_expense,
                    amount_expense_valued,
                    amount_gain
            """

    def _from(self, model, models):
        return f"FROM {model.replace('.', '_')}"

    def _join(self, model, models):
        return ''
    
    def _where(self, model, models):
        if model == 'account.move.budget.line':
            return """
                WHERE
                    type = 'amount' AND balance != 0.0
                    OR qty_balance != 0.0
            """
        return ''
    
    def _groupby(self, model, models):
        return ''
    
    def _orderby(self, model, models):
        return ''

    def _having(self, model, models):
        return ''
