# -*- coding: utf-8 -*-

from odoo import models, tools, fields
from psycopg2.extensions import AsIs

class CarpentryBudgetExpenseDistributed(models.Model):
    """ Estimate the expense of a PO/MO/... distributed per launch,
        i.e. per line of budget reservation using as distribution key:
        [Total reserved on this launch & budget] / [Total reserved on this budget]
    """
    _name = 'carpentry.budget.expense.distributed'
    _inherit = ['carpentry.budget.expense']
    _description = 'Expenses per Launchs'
    _auto = False

    launch_id = fields.Many2one(readonly=True,store=True,)

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
                {having}
            )""" . format (
                view_name=AsIs(self._table),
                select=AsIs(self._select()),
                from_table=AsIs(self._from()),
                join=AsIs(self._join()),
                where=AsIs(self._where()),
                groupby=AsIs(self._groupby()),
                orderby=AsIs(self._orderby()),
                having=AsIs(self._having()),
        ))

    def _select(self):
        budget_types = self.env['account.analytic.account']._get_budget_type_workforce()
        return f"""
            SELECT
                row_number() OVER (ORDER BY 
                    reservation.sequence_record,
                    reservation.sequence_aac,
                    reservation.sequence_launch,
                    reservation.id
                ) AS id,
                reservation.project_id,
                reservation.launch_id,
                {self._get_sql_record_fields()},
                reservation.active,
                
                reservation.budget_type,
                reservation.analytic_account_id,

                -- amount_reserved
                SUM(reservation.amount_reserved) AS amount_reserved,
                SUM(reservation.amount_reserved)  * (
                    CASE
                        WHEN reservation.budget_type IN {tuple(budget_types)}
                        THEN AVG(expense.hourly_cost_coef)
                        ELSE 1.0
                    END
                ) AS amount_reserved_valued,
                
                -- amount_expense
                SUM(expense.amount_expense) * CASE
                    WHEN SUM(expense.amount_reserved) = 0.0
                    THEN 1.0
                    --   reserved budget of this launch on this aac
                    --   / reserved budget on this aac, for all launches
                    ELSE SUM(reservation.amount_reserved) / SUM(expense.amount_reserved)
                END AS amount_expense,
                
                -- amount_expense_valued
                SUM(expense.amount_expense_valued) * CASE
                    WHEN SUM(expense.amount_reserved) = 0.0
                    THEN 1.0
                    ELSE SUM(reservation.amount_reserved) / SUM(expense.amount_reserved)
                END AS amount_expense_valued,
                
                -- amount_gain
                SUM(expense.amount_gain) * CASE
                    WHEN SUM(expense.amount_reserved) = 0.0
                    THEN 1.0
                    ELSE SUM(reservation.amount_reserved) / SUM(expense.amount_reserved)
                END AS amount_gain
        """

    def _from(self):
        return 'FROM carpentry_budget_reservation AS reservation'

    def _join(self):
        # SQL for balance_id, purchase_id, production_id, task_id, ...
        record_fields = self.env['carpentry.budget.reservation']._get_record_fields()
        sql_record_fields = ' OR ' . join([f'expense.{field} = reservation.{field}' for field in record_fields])
        
        return f"""
            INNER JOIN carpentry_budget_expense AS expense
                -- expense is record's line, which amount must be distributed
                -- on the several record's launchs as per launch's reserved budget / total reserved budget
                -- for the line's analytic account
                ON  expense.analytic_account_id = reservation.analytic_account_id
                AND {sql_record_fields}
        """

    def _where(self):
        return ''
    
    def _groupby(self):
        
        return f"""
            GROUP BY
                -- record is not grouped by launch,
                -- but reservation is => we can distribute thanks to
                -- record.amount_reserved / reservation.amount_reserved
                expense.id,
                reservation.id,
                reservation.project_id,
                {self._get_sql_record_fields()},
                reservation.active,
                reservation.budget_type,
                reservation.analytic_account_id,
                reservation.launch_id,
                -- sequences
                reservation.sequence_record,
                reservation.sequence_aac,
                reservation.sequence_launch
        """
    
    def _orderby(self):
        return ''

    def _having(self):
        return ''
    
    def _get_sql_record_fields(self):
        record_fields = self.env['carpentry.budget.reservation']._get_record_fields()
        return ', ' . join(['reservation.' + field for field in record_fields])