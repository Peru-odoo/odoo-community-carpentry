# -*- coding: utf-8 -*-

from odoo import models, tools, fields
from psycopg2.extensions import AsIs

class CarpentryBudgetExpenseDistributed(models.Model):
    """ Estimate the expense of a PO/MO/... distributed per launch,
        i.e. per line of budget reservation using as distribution key:
        [Total reserved on this launch & budget] / [Total reserved on this budget]

        This is needed for planning, to estimate expense per launch
    """
    _name = 'carpentry.budget.expense.distributed'
    _inherit = ['carpentry.budget.expense']
    _description = 'Expenses per Launchs'
    _auto = False

    expense_distributed = fields.Float(
        string='Distributed expense',
        digits='Product price',
        readonly=True,
    )
    launch_id = fields.Many2one(store=True)

    #===== View build =====#
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self._cr.execute("""
            CREATE or REPLACE VIEW {view_name} AS (
                {select}
                {from_table}
                {join}
                {where}
                {groupby}
                {orderby}
            )""" . format (
                view_name=AsIs(self._table),
                select=AsIs(self._select()),
                from_table=AsIs(self._from()),
                join=AsIs(self._join()),
                where=AsIs(self._where()),
                groupby=AsIs(self._groupby()),
                orderby=AsIs(self._orderby()),
        ))

    def _select(self):
        return """
            SELECT
                row_number() OVER (ORDER BY 
                    affectation.section_id,
                    affectation.section_model_id,
                    affectation.group_id,
                    affectation.record_id
                ) AS id,
                affectation.project_id,
                affectation.section_id,
                affectation.section_model_id,
                
                affectation.budget_type,
                affectation.group_id AS analytic_account_id,

                affectation.record_id AS launch_id,

                -- expense
                SUM(expense.amount_expense) / COUNT(affectation_total.id) AS amount_expense,

                -- reserved budget of this launch on this aac
                SUM(affectation.quantity_affected) / COUNT(affectation_total.id) AS quantity_affected,
                
                -- total reserved budget of this aac (on a given section), summed on several launchs
                SUM(affectation_total.quantity_affected) AS sum_quantity_affected,

                (
                    SUM(expense.amount_expense) / COUNT(affectation_total.id) * (
                        SUM(affectation.quantity_affected) / COUNT(affectation_total.id) / -- reserved budget of this launch on this aac
                        SUM(affectation_total.quantity_affected) -- reserved budget on this aac, for all launches
                    )
                ) AS expense_distributed
        """

    def _from(self):
        return 'FROM carpentry_group_affectation AS affectation'

    def _join(self):
        return """
            INNER JOIN carpentry_budget_expense AS expense
                -- expense is section's line, which amount must be distributed
                -- on the several section's launchs as per launch's reserved budget / total reserved budget
                -- for the line's analytic account
                ON  expense.section_id = affectation.section_id
                AND expense.section_model_id = affectation.section_model_id
                AND expense.analytic_account_id = affectation.group_id

            LEFT JOIN carpentry_group_affectation AS affectation_total
                -- same document/section (e.g. PO)
                ON  affectation_total.section_id = affectation.section_id
                AND affectation_total.section_model_id = affectation.section_model_id
                -- same budget (and possibly several launches)
                AND affectation_total.group_id = affectation.group_id
                AND affectation_total.quantity_affected != 0.0
        """

    def _where(self):
        return """
            WHERE
                expense.state = 'expense' AND
                expense.amount_expense != 0.0 AND
                affectation.budget_type IS NOT NULL AND
                affectation.quantity_affected != 0.0
            """
    
    def _groupby(self):
        return """
            GROUP BY
                affectation.project_id,
                affectation.section_id,
                affectation.section_model_id,
                affectation.budget_type,
                affectation.group_id,
                affectation.record_id
        """
    
    def _orderby(self):
        return ''
