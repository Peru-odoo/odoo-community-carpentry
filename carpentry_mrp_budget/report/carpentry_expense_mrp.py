# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryExpense(models.Model):
    _inherit = ['carpentry.budget.expense.history']

    #===== View build =====#
    def _get_queries_models(self):
        """ == Stock moves== 
            * `stock.picking`:  for stock.move estimation before validation
            * `mrp.production`: same, for raw material
            For those 2, expense is summed from `stock.valuation.layer`
            when they are done, for final/accountable value
            
            == Work orders ==
            * `mrp.workorder`: manufacturing times
        """
        return super()._get_queries_models() + (
            'stock.picking', # lines are stock.move (move_ids)
            'mrp.production', # lines are stock.move too (move_raw_ids)
            'mrp.workorder' # lines are mrp.workorders (actually: mrp.workcenter.productivity)
        )
    
    def _select(self, model, models):
        sql_active = "record.state NOT IN ('cancel')"
        if model in ('mrp.production', 'mrp.workorder'):
            sql_active + " AND record.active"
        
        if model in ('stock.picking', 'mrp.production'):
            sign = (
                "CASE WHEN picking_type.code = 'incoming' THEN -1 ELSE 1 END"
                if model == 'stock.picking'
                else 1
            )
            
            return f"""
                SELECT
                    record.project_id,
                    record.date_budget AS date,
                    {sql_active} AS active,
                    record.id AS record_id,
                    {models[model]} AS record_model_id,
                    analytic.id AS analytic_account_id,
                    analytic.budget_type,

                    CASE
                        WHEN COALESCE(COUNT(reservation.id), 0.0) != 0
                        THEN SUM(reservation.amount_reserved) / COUNT(reservation.id)
                        ELSE 0.0
                    END AS amount_reserved,
                    
                    -- expense: will be devaluated for workforce
                    'DEVALUE' AS value_or_devalue_workforce_expense,
                    SUM(
                        CASE
                            WHEN record.state = 'done'
                            THEN ABS(svl.value) -- accounting value
                            ELSE line.product_uom_qty::float * property.value_float::float -- estimation
                        END
                        * analytic_distribution.percentage::float
                        / 100.0
                    ) * {sign} AS amount_expense,

                    -- valued expense: will be calculated from `amount_expense` (without devaluation)
                    NULL AS amount_expense_valued
            """
        
        elif model == 'mrp.workorder':
            return f"""
                SELECT
                    record.project_id AS project_id,
                    record.date_budget_workorders AS date,
                    {sql_active} AS active,
                    record.id AS record_id,
                    {models['mrp.production']} AS record_model_id,
                    analytic.id AS analytic_account_id,
                    analytic.budget_type,
                    
                    -- amount_reserved:
                    -- 1. if effective_hours < amount_reserved:
                    --    displays expense == budget_reservation in the project's budget report
                    CASE
                        WHEN record.state != 'done' AND SUM(line.duration) / 60 < COALESCE(SUM(reservation.amount_reserved), 0.0)
                        THEN SUM(line.duration) / 60
                        ELSE COALESCE(SUM(reservation.amount_reserved), 0.0)
                    END *
                    CASE -- prorata per workorder's reserved budget
                        WHEN record.total_budget_reserved != 0.0
                        THEN COALESCE(SUM(reservation.amount_reserved), 0.0) / record.total_budget_reserved
                        ELSE 0.0
                    END AS amount_reserved,
                    
                    -- expense
                    'VALUE' AS value_or_devalue_workforce_expense,
                    SUM(line.duration) / 60 *
                    CASE -- prorata per workorder's reserved budget
                        WHEN record.total_budget_reserved != 0.0
                        THEN COALESCE(SUM(reservation.amount_reserved), 0.0) / record.total_budget_reserved 
                        ELSE 1.0
                    END AS amount_expense,

                    -- expense valued: will be calculated from `amount_expense` and valued (for workforce)
                    NULL AS amount_expense_valued
            """
        
        return super()._select(model, models)
    
    def _from(self, model, models):
        if model in ('stock.picking', 'mrp.production'):
            return 'FROM stock_move AS line'
        elif model == 'mrp.workorder':
            return 'FROM mrp_workorder AS line'
        else:
            return super()._from(model, models)
    
    def _join(self, model, models):
        sql = ''

        if model in ('stock.picking', 'mrp.production'):
            sql += self._join_product_analytic_distribution()

            if model == 'stock.picking':
                sql += """
                    INNER JOIN stock_picking AS record
                        ON record.id = line.picking_id
                    INNER JOIN stock_picking_type AS picking_type
                        ON picking_type.id = record.picking_type_id
                """
            else:
                sql += """
                    INNER JOIN mrp_production AS record
                        ON record.id = line.raw_material_production_id
                """
            sql += f"""
                LEFT JOIN stock_valuation_layer AS svl
                    ON svl.stock_move_id = line.id
                
                INNER JOIN project_project AS project
                    ON project.id = record.project_id
                LEFT JOIN ir_property AS property
                    ON  property.res_id = 'product.product,' || product_product.id
                    AND property.company_id = project.company_id
            """
        
        elif model == 'mrp.workorder':
            sql += f"""
                INNER JOIN mrp_production AS record
                    ON record.id = line.production_id
            """
        
        # reservations
        if model in ('stock.picking', 'mrp.production', 'mrp.workorder'):
            sql += f"""
                LEFT JOIN carpentry_budget_reservation AS reservation
                    ON  reservation.{self.env[model]._record_field} = record.id
            """
            if model in ('stock.picking', 'mrp.production'):
                sql += " AND reservation.analytic_account_id = analytic.id"
            elif model == 'mrp.workorder':
                budget_types = self.env['account.analytic.account']._get_budget_type_workforce()
                sql += f"""
                        AND reservation.budget_type IN {tuple(budget_types)}
                    LEFT JOIN account_analytic_account AS analytic
                        ON analytic.id = reservation.analytic_account_id
                """
        
        return sql + super()._join(model, models)
        
    
    def _where(self, model, models):
        sql = super()._where(model, models)

        if model == 'stock.picking':
            sql += """
                AND picking_type.code != 'internal'
                AND line.purchase_line_id IS NULL -- stock_move.purchase_line_id
                AND line.production_id IS NULL
                AND line.raw_material_production_id IS NULL
            """
        
        return sql

    def _groupby(self, model, models):
        res = super()._groupby(model, models)
        
        if model == 'mrp.workorder':
            res += ', line.project_id, line.productivity_tracking'
        elif model == 'stock.picking':
            res += ', picking_type.code'
        
        return res
    
