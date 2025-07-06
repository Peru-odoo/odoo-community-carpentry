# -*- coding: utf-8 -*-

from odoo import models

class CarpentryExpense(models.Model):
    _inherit = ['carpentry.budget.expense']

    #===== View build =====#
    def _get_queries_models(self):
        """ stock.picking: for stock move estimation before validation (done)
            mrp.production: same, for raw material
            stock.valuation.layer: final/accountable value when done
        """
        return super()._get_queries_models() + (
            'stock.picking','mrp.production', # for product stock
            'mrp.workorder' # for production times (section is changed back to mrp.production)
        )
    
    def _select(self, model, models):
        sql = super()._select(model, models)
        
        if model in ('stock.picking', 'mrp.production'):
            sql += """
                -- expense
                SUM(
                    CASE
                        WHEN section.state = 'done'
                        THEN ABS(svl.value) -- accounting value
                        ELSE line.product_uom_qty::float * property.value_float::float -- estimation
                    END
                    * analytic_distribution.percentage::float
                    / 100.0
                ) AS amount_expense,
                
                -- gain
                0.0 AS amout_gain,
                TRUE AS should_compute_gain,
                FALSE AS should_value_expense
            """
        elif model == 'mrp.workorder':
            sql += """
                -- expense
                SUM(line.duration) / 60.0 AS amount_expense, -- /60 for min to hours conversion
                
                -- gain
                CASE
                    WHEN SUM(line.duration) > SUM(line.duration_expected) OR section.state = 'done'
                    THEN (SUM(line.duration_expected) - SUM(line.duration)) / 60.0
                    ELSE CASE
                        WHEN line.productivity_tracking = 'unit' AND SUM(line.qty_production) != 0.0 AND SUM(line.qty_produced) != 0.0
                        THEN
                            (SUM(line.duration_expected) / SUM(line.qty_production)
                            - SUM(line.duration) / SUM(line.qty_produced)
                            ) * SUM(line.qty_produced) / 60.0
                        ELSE 0.0
                    END
                END AS amount_gain,
                FALSE AS should_compute_gain,
                TRUE AS should_value_expense
            """
        
        return sql
    
    def _get_section_fields(self, model, models):
        """ Resolve mrp.workorder indicators as mrp.production's
            in the pivot and tree view,

            and compute gain as per workorder qty logics
        """
        return (
            {
                'section_id': 'section.id',
                'section_ref': f"'mrp.production,' || section.id",
                'section_model_id': models['mrp.production'],
            }
            if model == 'mrp.workorder'
            else super()._get_section_fields(model, models)
        )
    
    def _from(self, model, models):
        if model in ('stock.picking', 'mrp.production'):
            return 'FROM stock_move AS line'
        elif model == 'mrp.workorder':
            return 'FROM mrp_workorder AS line'
        else:
            return super()._from(model, models)
    
    def _join(self, model, models):
        sql_before, sql_after = '', ''

        if model in ('stock.picking', 'mrp.production'):
            if model == 'stock.picking':
                sql_before = """
                    INNER JOIN stock_picking AS section
                        ON section.id = line.picking_id
                    INNER JOIN stock_picking_type AS picking_type
                        ON picking_type.id = section.picking_type_id
                """
            else:
                sql_before = """
                    INNER JOIN mrp_production AS section
                        ON section.id = line.raw_material_production_id
                """
            
            sql_after = """
                LEFT JOIN stock_valuation_layer AS svl
                    ON svl.stock_move_id = line.id
                
                INNER JOIN project_project AS project
                    ON project.id = section.project_id
                LEFT JOIN ir_property AS property
                    ON
                        property.res_id = 'product.product,' || product_product.id AND
                        property.company_id = project.company_id
            """

        elif model == 'mrp.workorder':
            return """
                -- section
                INNER JOIN mrp_production AS section
                    ON section.id = line.production_id
                
                -- analytic
                INNER JOIN mrp_workcenter AS workcenter
                    ON workcenter.id = line.workcenter_id
                LEFT JOIN account_analytic_account AS analytic
                    ON analytic.id = workcenter.costs_hour_account_id
            """
        
        return sql_before + super()._join(model, models) + sql_after
    
    def _where(self, model, models):
        sql = super()._where(model, models)

        if model in ('stock.picking', 'mrp.production', 'mrp.workorder'):
            sql += """
                AND section.state NOT IN ('draft', 'cancel')
            """
            
            if model == 'stock.picking':
                sql += """
                    AND picking_type.code != 'internal'
                    AND line.purchase_line_id IS NULL -- stock_move.purchase_line_id
                    AND line.production_id IS NULL
                    AND line.raw_material_production_id IS NULL
                """
        
        return sql

    def _groupby(self, model, models):
        return super()._groupby(model, models) + (
            ', line.productivity_tracking'
            if model == 'mrp.workorder'
            else ''
        )
