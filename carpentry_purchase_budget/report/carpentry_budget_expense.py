# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryExpense(models.Model):
    """ Should be overriden in each Carpentry module with expense """
    _inherit = ['carpentry.budget.expense']

    #===== View build =====#
    def _get_queries_models(self):
        """ Actually:
            - po lines with qty_invoice == 0, open PO on tree view click
            - mo lines, open MO
        """
        return super()._get_queries_models() + ('purchase.order','account.move',)
    
    def _select(self, model, models):
        sql = super()._select(model, models)
        
        if model in ('purchase.order', 'account.move'):
            ratio_invoiced = (
                '(line.product_qty::float - line.qty_invoiced::float) / line.product_qty::float'
                if model == 'purchase.order'
                else 1.0
            )

            sql += f"""
                -- expense
                SUM(
                    line.price_subtotal::float
                    * {ratio_invoiced}
                    * analytic_distribution.percentage::float
                    / 100.0
                ) AS amount_expense,
                
                -- gain
                0.0 AS amount_gain,
                TRUE AS should_compute_gain,
                TRUE AS should_value
            """
        
        return sql

    def _get_section_fields(self, model, models):
        """ display account move costs as/in purchase orders lines/columns """
        return (
            {
                'section_id': 'purchase_order_line.order_id',
                'section_ref': "'purchase.order,' || purchase_order_line.order_id",
                'section_model_id': models['purchase.order'],
            }
            if model == 'account.move'
            else super()._get_section_fields(model, models)
        )

    def _from(self, model, models):
        return (
            f"FROM {model.replace('.', '_')}_line AS line"

            if model in ('purchase.order', 'account.move')

            else super()._from(model, models)
        )
    
    def _join(self, model, models):
        sql =''
        if model == 'purchase.order':
            sql = """
                INNER JOIN purchase_order AS section
                    ON section.id = line.order_id
            """
        elif model == 'account.move':
            sql = """
                INNER JOIN account_move AS section
                    ON section.id = line.move_id
                INNER JOIN purchase_order_line
                    ON purchase_order_line.id = line.purchase_line_id
            """
        
        return sql + super()._join(model, models)
    
    def _where(self, model, models):
        sql = super()._where(model, models)
        
        if model in ('purchase.order', 'account.move'):
            sql += """
                AND section.state NOT IN ('draft', 'cancel')
                AND product_template.type != 'product' -- not stock
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
