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
                    reservation.section_id,
                    reservation.section_model_id,
                    reservation.analytic_account_id,
                    reservation.launch_id
                ) AS id,
                reservation.project_id,
                reservation.section_id,
                reservation.section_model_id,
                reservation.active,
                
                reservation.budget_type,
                reservation.analytic_account_id,

                reservation.launch_id,

                -- amount_reserved
                SUM(reservation.amount_reserved) / (
                    CASE
                        WHEN COUNT(reservation_total.id) = 0
                        THEN 1
                        ELSE COUNT(reservation_total.id)
                    END
                ) AS amount_reserved,

                -- amount_reserved_valued
                SUM(reservation.amount_reserved) / (
                    CASE
                        WHEN COUNT(reservation_total.id) = 0
                        THEN 1
                        ELSE COUNT(reservation_total.id)
                    END
                ) * (
                    CASE
                        WHEN reservation.budget_type IN {tuple(budget_types)}
                        THEN hourly_cost.coef
                        ELSE 1.0
                    END
                ) AS amount_reserved_valued,
                
                -- amount_expense
                CASE
                    WHEN COUNT(reservation_total.id) = 0 OR SUM(reservation_total.amount_reserved) = 0.0
                    THEN SUM(expense.amount_expense)
                    ELSE (
                        SUM(expense.amount_expense) / COUNT(reservation_total.id) * (
                            SUM(reservation.amount_reserved) / COUNT(reservation_total.id) / -- reserved budget of this launch on this aac
                            SUM(reservation_total.amount_reserved) -- reserved budget on this aac, for all launches
                        )
                    )
                END AS amount_expense,
                
                -- amount_expense_valued
                CASE
                    WHEN COUNT(reservation_total.id) = 0 OR SUM(reservation_total.amount_reserved) = 0.0
                    THEN SUM(expense.amount_expense_valued)
                    ELSE (
                        SUM(expense.amount_expense_valued) / COUNT(reservation_total.id) * (
                            SUM(reservation.amount_reserved) / COUNT(reservation_total.id) / -- reserved budget of this launch on this aac
                            SUM(reservation_total.amount_reserved) -- reserved budget on this aac, for all launches
                        )
                    )
                END AS amount_expense_valued,
                
                -- amount_gain
                CASE
                    WHEN COUNT(reservation_total.id) = 0 OR SUM(reservation_total.amount_reserved) = 0.0
                    THEN SUM(expense.amount_gain)
                    ELSE (
                        SUM(expense.amount_gain) / COUNT(reservation_total.id) * (
                            SUM(reservation.amount_reserved) / COUNT(reservation_total.id) / -- reserved budget of this launch on this aac
                            SUM(reservation_total.amount_reserved) -- reserved budget on this aac, for all launches
                        )
                    )
                END AS amount_gain
        """

    def _from(self):
        return 'FROM carpentry_budget_expense AS expense'

    def _join(self):
        return """
            LEFT JOIN carpentry_budget_reservation AS reservation
                -- expense is section's line, which amount must be distributed
                -- on the several section's launchs as per launch's reserved budget / total reserved budget
                -- for the line's analytic account
                ON  reservation.section_id = expense.section_id
                AND reservation.section_model_id = expense.section_model_id
                AND reservation.analytic_account_id = expense.analytic_account_id

            LEFT JOIN carpentry_budget_reservation AS reservation_total
                -- same document/section (e.g. PO)
                ON  reservation_total.section_id = reservation.section_id
                AND reservation_total.section_model_id = reservation.section_model_id
                -- same budget (and possibly several launches)
                AND reservation_total.analytic_account_id = reservation.analytic_account_id
                AND reservation_total.amount_reserved != 0.0
            
            -- for (h) to (€) valuation when needed
            LEFT JOIN carpentry_budget_hourly_cost AS hourly_cost
                ON  hourly_cost.project_id = reservation.project_id
                AND hourly_cost.analytic_account_id = reservation.analytic_account_id
        """

    def _where(self):
        return ''
    
    def _groupby(self):
        return """
            GROUP BY
                reservation.project_id,
                reservation.section_id,
                reservation.section_model_id,
                reservation.active,
                reservation.budget_type,
                reservation.analytic_account_id,
                reservation.launch_id,
                hourly_cost.coef
        """
    
    def _orderby(self):
        return ''

    def _having(self):
        return ''
    