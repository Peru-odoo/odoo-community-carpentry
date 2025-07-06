# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from psycopg2.extensions import AsIs

class CarpentryBudgetExpense(models.Model):
    """ Should be overriden in each Carpentry module with expense """
    _name = 'carpentry.budget.expense'
    _inherit = ['carpentry.budget.remaining']
    _description = 'Expenses'
    _auto = False

    #===== Fields =====#
    currency_id = fields.Many2one(
        related='project_id.currency_id',
    )
    date = fields.Date(
        string='Date',
        readonly=True,
    )
    state = fields.Selection(
        selection_add=[('expense', 'Expense')]
    )
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
            budget_types = self.env['account.analytic.account']._get_budget_type_workforce()
            self._cr.execute("""
                CREATE or REPLACE VIEW %(view_name)s AS (
                    SELECT
                        row_number() OVER (ORDER BY
                            expense.section_id,
                            expense.section_model_id,
                            expense.analytic_account_id
                        ) AS id,
                        expense.state,
                        expense.project_id,
                        expense.date,
                        
                        expense.section_id,
                        expense.section_model_id,
                        expense.analytic_account_id,
                        expense.budget_type,
                        
                        -- reserved budget
                        SUM(expense.quantity_affected) * (
                        CASE
                            WHEN expense.budget_type IN %(budget_types)s
                            THEN hourly_cost.coef
                            ELSE 1.0
                        END) AS quantity_affected,
                        
                        -- expense
                        SUM(expense.amount_expense) * (
                        CASE
                            WHEN expense.budget_type IN %(budget_types)s AND NOT(false = ANY(ARRAY_AGG(should_value_expense)))
                            THEN hourly_cost.coef
                            ELSE 1.0
                        END) AS amount_expense,
                        
                        -- gain
                        (CASE
                            WHEN (false = ANY(ARRAY_AGG(should_compute_gain)))
                            THEN SUM(amount_gain) * (
                                    CASE
                                        WHEN expense.budget_type IN %(budget_types)s AND NOT(false = ANY(ARRAY_AGG(should_value_expense)))
                                        THEN hourly_cost.coef
                                        ELSE 1.0
                                    END
                                )
                            ELSE
                                SUM(quantity_affected) * (
                                    CASE
                                        WHEN expense.budget_type IN %(budget_types)s
                                        THEN hourly_cost.coef
                                        ELSE 1.0
                                    END
                                )
                                - SUM(amount_expense) * (
                                    CASE
                                        WHEN expense.budget_type IN %(budget_types)s AND true = ALL(ARRAY_AGG(should_value_expense))
                                        THEN hourly_cost.coef
                                        ELSE 1.0
                                    END
                                )
                        END) AS amount_gain
                    
                    FROM (
                        (%(union)s)
                    ) AS expense
                    
                    -- for (h) to (€) valuation when needed (on PO)
                    LEFT JOIN carpentry_budget_hourly_cost AS hourly_cost
                        ON  hourly_cost.project_id = expense.project_id
                        AND hourly_cost.analytic_account_id = expense.analytic_account_id
                    
                    GROUP BY
                        expense.state,
                        expense.project_id,
                        expense.date,
                        expense.section_id,
                        expense.section_model_id,
                        expense.analytic_account_id,
                        expense.budget_type,
                        hourly_cost.coef
                    ORDER BY
                        expense.section_id
                )""", {
                    'view_name': AsIs(self._table),
                    'budget_types': tuple(budget_types),
                    'union': AsIs(') UNION ALL (' . join(queries)),
            })
    
    def _get_section_fields(self, model, models):
        """ Can be overwritten """
        return {
            'section_id': 'section.id',
            'section_model_id': models[model],
        }

    def _select(self, model, models):
        section_fields = self._get_section_fields(model, models)

        # general
        if model == 'carpentry.group.affectation':
            sql = f"""
                SELECT
                    'reservation' AS state,
                    affectation.project_id,
                    affectation.section_id AS section_id,
                    affectation.section_model_id,
                    affectation.group_id AS analytic_account_id,
                    affectation.budget_type,
                    affectation.quantity_affected,
                    affectation.date,
                    0.0 AS amount_expense,
                    0.0 AS amount_gain,
                    TRUE AS should_compute_gain,
                    TRUE AS should_value_expense
            """
        else:
            # specific : no budget reservation (`quantity_affected`)
            # but `amount_expense` (except carpentry.budget.balance)
            Model = self.env[model]
            sql = f"""
                SELECT
                    'expense' AS state,
                    
                    -- project & section
                    section.project_id,
                    {section_fields['section_id']} AS section_id,
                    {section_fields['section_model_id']} AS section_model_id,

                    -- budget,
                    analytic.id AS analytic_account_id,
                    analytic.budget_type,
                    0.0 AS quantity_affected,
                    section.{Model._get_budget_date_field()} AS date,
            """
        
        # specific to budget balance
        if model == 'carpentry.budget.balance':
            sql += """
                    0.0 AS amount_expense,
                    0.0 AS amout_gain,
                    TRUE AS should_compute_gain,
                    TRUE AS should_value_expense
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
                affectation.group_model_id = {models['account.analytic.account']} AND
                active IS TRUE
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
