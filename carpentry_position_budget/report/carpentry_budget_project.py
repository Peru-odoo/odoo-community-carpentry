# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from psycopg2.extensions import AsIs



class CarpentryBudgetProject(models.Model):
    """ Should be overriden in each Carpentry module with expense """
    _name = 'carpentry.budget.project'
    _inherit = ['carpentry.budget.expense']
    _description = 'Budget project balance'
    _auto = False
    _order = 'project_id, sequence'

    #===== Fields =====#
    sequence = fields.Integer()
    available = fields.Float(
        string='Available budget',
        digits='Product price',
        readonly=True,
    )
    quantity_affected = fields.Float(
        string='Reserved budget',
        digits='Product Unit of Measure',
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
                
                section_id AS section_id,
                section_model_id,
                
                SUM(available) AS available,
                SUM(quantity_affected) AS quantity_affected,
                SUM(amount_expense) AS amount_expense,
                SUM(amount_gain) AS amount_gain,
                CASE
                    WHEN SUM(quantity_affected) != 0
                    THEN SUM(amount_gain) / SUM(quantity_affected) * 100.0 
                    ELSE 0.0
                END AS percent_gain
        """
    
    def _view_groupby(self):
        return """
            GROUP BY
                project_id,
                result.budget_type,
                analytic_account_id,
                section_id,
                section_model_id,
                sequence
        """
    
    
    def _select(self, model, models):
        if model == 'account.move.budget.line':
            return f"""
                SELECT 
                    'budget' AS state,

                    project_id,
                    budget_type,
                    analytic_account_id,
                    id AS section_id,
                    {models['account.move.budget.line']} AS section_model_id,

                    balance AS available, -- always valued
                    0.0 AS quantity_affected,
                    0.0 AS amount_gain,
                    0.0 AS amount_expense
            """
        else:
            return """
                SELECT
                    'expense' AS state,

                    project_id,
                    budget_type,
                    analytic_account_id,
                    section_id,
                    section_model_id,

                    0.0 AS available,
                    quantity_affected,
                    amount_gain,
                    amount_expense
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

