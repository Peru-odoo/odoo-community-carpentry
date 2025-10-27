# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryExpenseHistory(models.Model):
    _inherit = ['carpentry.budget.expense.history']

    #===== View build =====#
    def _get_queries_models(self):
        """ Actually:
            - po lines with qty_invoice == 0, open PO on tree view click
            - mo lines, open MO
        """
        return super()._get_queries_models() + ('purchase.order','account.move',)
    
    def _select(self, model, models):
        if model in ('purchase.order', 'account.move'):
            ratio_invoiced = (
                '(line.product_qty::float - line.qty_invoiced::float) / line.product_qty::float'
                if model == 'purchase.order'
                else 1.0
            )

            sql_section_id = 'section.id'
            if model == 'account.move':
                sql_section_id = 'purchase_order_line.order_id'
            
            return f"""
                SELECT
                    section.project_id,
                    section.date_budget AS date,
                    section.state NOT IN ('cancel') as active,
                    {sql_section_id} AS section_id,
                    {models['purchase.order']} AS section_model_id,
                    analytic.id AS analytic_account_id,
                    analytic.budget_type,

                    0.0 AS amount_reserved,
                    TRUE AS should_devalue_workforce_expense,

                    -- expense
                    SUM(
                        line.price_subtotal::float
                        * {ratio_invoiced}
                        * analytic_distribution.percentage::float
                        / 100.0
                    ) AS amount_expense,
                    
                    -- expense valued
                    SUM(
                        line.price_subtotal::float
                        * {ratio_invoiced}
                        * analytic_distribution.percentage::float
                        / 100.0
                    ) AS amount_expense_valued
            """
        
        return super()._select(model, models)

    def _from(self, model, models):
        if model in ('purchase.order', 'account.move'):
            return f"FROM {model.replace('.', '_')}_line AS line"
        else:
            return super()._from(model, models)
    
    def _join(self, model, models):
        sql = ''
        if model in ('purchase.order', 'account.move'):
            sql = self._join_product_analytic_distribution()
            
            if model == 'purchase.order':
                sql += """
                    INNER JOIN purchase_order AS section
                        ON section.id = line.order_id
                """
            elif model == 'account.move':
                sql += """
                    INNER JOIN account_move AS section
                        ON section.id = line.move_id
                    INNER JOIN purchase_order_line
                        ON purchase_order_line.id = line.purchase_line_id
                """
        
        return sql + super()._join(model, models)
    
    def _where(self, model, models):
        sql = super()._where(model, models)
        
        if model in ('purchase.order', 'account.move'):
            clause = " WHERE" if not sql else " AND"
            sql += clause + """
                product_template.type != 'product' -- not stock
            """

            if model == 'purchase.order':
                sql += """
                    AND line.qty_invoiced < line.product_qty
                    AND product_qty != 0.0
                    AND line.display_type IS NULL
                """
            else:
                sql += "AND line.display_type NOT IN ('line_section', 'line_note')"
        
        return sql
    
    def _groupby(self, model, models):
        sql = super()._groupby(model, models)

        if model == 'account.move':
            sql += ', purchase_order_line.order_id'
        
        return sql
