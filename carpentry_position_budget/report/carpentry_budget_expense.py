# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from psycopg2.extensions import AsIs

class CarpentryBudgetExpense(models.Model):
    """ Should be overriden in each Carpentry module with expense """
    _name = 'carpentry.budget.expense'
    _inherit = ['carpentry.budget.remaining']
    _description = 'Budget-related expense report'
    _auto = False

    #===== Fields =====#
    launch_ids = fields.Many2many(
        string='Launchs',
        comodel_name='carpentry.group.launch',
        compute='_compute_launch_ids',
    )
    amount_expense = fields.Float(
        string='Real expense',
        digits='Product price',
        readonly=True,
    )
    amount_gain = fields.Float(
        string='Gain or Loss',
        digits='Product price',
        readonly=True,
        help='Budget reservation - Real expense',
    )

    # cancel fields
    state = fields.Selection(store=False)
    launch_id = fields.Many2one(store=False)
    group_model_id = fields.Many2one(store=False)
    group_res_model = fields.Char(related='', store=False)


    #===== View build =====#
    def _get_queries_models(self):
        """ Inherited in sub-modules (purchase, mrp, timesheet) """
        return ('carpentry.group.affectation', 'carpentry.budget.balance',)
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        queries = self._get_queries()
        if queries:
            self._cr.execute("""
                CREATE or REPLACE VIEW %s AS (
                    SELECT
                        row_number() OVER (ORDER BY section_ref, analytic_account_id) AS id,
                        project_id,
                        section_ref,
                        section_model_id,
                        analytic_account_id,
                        budget_type,
                        SUM(quantity_affected) AS quantity_affected,
                        SUM(amount_expense) AS amount_expense,
                        CASE
                            WHEN NOT (false = ANY(ARRAY_AGG(should_compute_gain)))
                            THEN SUM(quantity_affected) - SUM(amount_expense)
                            ELSE 0.0
                        END AS amount_gain
                    FROM (
                        (%s)
                    ) AS result
                    GROUP BY
                        project_id,
                        section_id,
                        section_ref,
                        section_model_id,
                        analytic_account_id,
                        budget_type
                    ORDER BY
                        section_id
                )""", (
                    AsIs(self._table),
                    AsIs(') UNION ALL (' . join(queries))
                )
            )
    
    def _get_section_fields(self, model, models):
        """ Can be overwritten """
        return {
            'section_id': 'section.id',
            'section_ref': f"'{model},' || section.id",
            'section_model_id': models[model]
        }

    def _select(self, model, models):
        section_fields = self._get_section_fields(model, models)

        # general
        if model == 'carpentry.group.affectation':
            sql = f"""
                SELECT
                    affectation.project_id,
                    affectation.section_id AS section_id,
                    model.model || ',' || affectation.section_id AS section_ref,
                    affectation.section_model_id,
                    affectation.group_id AS analytic_account_id,
                    affectation.budget_type,
                    affectation.quantity_affected,
                    0.0 AS amount_expense,
                    TRUE AS should_compute_gain
            """
        else:
            # specific : no budget reservation (`quantity_affected`)
            # but `amount_expense` (except carpentry.budget.balance)
            sql = f"""
                SELECT
                    -- project & section_ref
                    section.project_id,
                    {section_fields['section_id']} AS section_id,
                    {section_fields['section_ref']} AS section_ref,
                    {section_fields['section_model_id']} AS section_model_id,

                    -- budget,
                    analytic.id AS analytic_account_id,
                    analytic.budget_type,
                    0.0 AS quantity_affected,
            """
        
        # specific to budget balance
        if model == 'carpentry.budget.balance':
            sql += """
                    0.0 AS amount_expense,
                    TRUE AS should_compute_gain
            """
        
        return sql

    def _from(self, model, models):
        return (
            'FROM carpentry_group_affectation AS affectation'
            
            if model == 'carpentry.group.affectation' else

            f"FROM {model.replace('.', '_')} AS section"
        )

    def _join(self, model, models):
        if model == 'carpentry.group.affectation':
            return """
                INNER JOIN ir_model AS model
                    ON model.id = affectation.section_model_id
            """
        elif model == 'carpentry.budget.balance':
            return """
                INNER JOIN carpentry_group_affectation AS affectation
                    ON affectation.section_id = section.id AND affectation.section_model_id = section_model_id
                
                INNER JOIN account_analytic_account AS analytic
                    ON analytic.id = affectation.group_id
            
            """
        else:
            return """

                INNER JOIN product_product
                    ON product_product.id = line.product_id
                INNER JOIN product_template
                    ON product_template.id = product_product.product_tmpl_id
                
                LEFT JOIN LATERAL
                    jsonb_each_text(line.analytic_distribution)
                    AS analytic_distribution (account_analytic_id, percentage)
                    ON true
                
                -- analytic
                LEFT JOIN account_analytic_account AS analytic
                    ON analytic.id = analytic_distribution.account_analytic_id::integer
            """
    
    def _where(self, model, models):
        return (f"""
            WHERE
                affectation.group_model_id = {models['account.analytic.account']}
            """
            
            if model == 'carpentry.group.affectation' else """

            WHERE
                (analytic.id IS NULL OR (
                analytic.is_project_budget IS TRUE AND
                analytic.budget_type IS NOT NULL))
            """
        )
    
    def _groupby(self, model, models):
        return (
            '' if model == 'carpentry.group.affectation' else
            'GROUP BY section.project_id, analytic.budget_type, analytic.id, section.id'
        )
    
    def _orderby(self, model, models):
        return ''

    #===== Compute =====#
    @api.depends('section_ref')
    def _compute_launch_ids(self):
        for expense in self:
            expense.launch_ids = (
                expense.section_ref and
                'launch_ids' in expense.section_ref and # for position, launch_ids does not exist
                expense.section_ref.launch_ids
            )
