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
                        
                        expense.section_id,
                        expense.section_model_id,
                        expense.analytic_account_id,
                        expense.budget_type,
                        
                        SUM(expense.amount_expense) AS amount_expense,
                        
                        -- quantity_affected (brut or valued)
                        CASE
                            WHEN budget_type NOT IN %(budget_types)s OR (false = ANY(ARRAY_AGG(should_value)))
                            THEN SUM(quantity_affected)
                            ELSE CASE
                                WHEN (
                                    project.date IS NULL OR project.date_start IS NULL
                                    OR project.date = project.date_start
                                )
                                THEN 0.0

                                -- valuation computation
                                ELSE SUM(
                                    (
                                        (
                                            LEAST(project.date, COALESCE(history.date_to, project.date)) -- overlap_end
                                            - GREATEST(project.date_start, history.starting_date) -- overlap_start
                                            + 1.0
                                        ) -- overlap_days
                                        /
                                        (project.date - project.date_start + 1.0) -- total_days
                                    ) -- weight_of_period
                                    * expense.quantity_affected * history.hourly_cost
                                )
                            END
                        END AS quantity_affected,
                        
                        CASE
                            WHEN (false = ANY(ARRAY_AGG(should_compute_gain)))
                            THEN SUM(amount_gain)
                            ELSE CASE -- quantity_affected
                                WHEN budget_type NOT IN %(budget_types)s OR (false = ANY(ARRAY_AGG(should_value)))
                                THEN SUM(quantity_affected)
                                ELSE CASE
                                    WHEN (
                                        project.date IS NULL OR project.date_start IS NULL
                                        OR project.date = project.date_start
                                    )
                                    THEN 0.0

                                    -- valuation computation
                                    ELSE SUM(
                                        (
                                            (
                                                LEAST(project.date, COALESCE(history.date_to, project.date)) -- overlap_end
                                                - GREATEST(project.date_start, history.starting_date) -- overlap_start
                                                + 1.0
                                            ) -- overlap_days
                                            /
                                            (project.date - project.date_start + 1.0) -- total_days
                                        ) -- weight_of_period
                                        * expense.quantity_affected * history.hourly_cost
                                    )
                                END
                            END - SUM(amount_expense)
                        END AS amount_gain
                    
                    FROM (
                        (%(union)s)
                    ) AS expense
                    
                    -- for (h) to (€) valuation when needed (on PO)
                    INNER JOIN project_project AS project
                        ON project.id = expense.project_id
                    LEFT JOIN hr_employee_timesheet_cost_history AS history
                        ON history.analytic_account_id = expense.analytic_account_id
                        AND expense.budget_type IN %(budget_types)s
                        AND project.date_start IS NOT NULL AND project.date IS NOT NULL AND (
                            history.starting_date IS NOT NULL AND (
                                history.starting_date BETWEEN project.date_start AND project.date OR
                                history.date_to       BETWEEN project.date_start AND project.date
                            )
                        )
                    
                    GROUP BY
                        expense.state,
                        expense.project_id,
                        expense.section_id,
                        expense.section_model_id,
                        expense.analytic_account_id,
                        expense.budget_type,
                        project.date,
                        project.date_start
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
                    0.0 AS amount_expense,
                    0.0 AS amount_gain,
                    TRUE AS should_compute_gain,
                    TRUE AS should_value
            """
        else:
            # specific : no budget reservation (`quantity_affected`)
            # but `amount_expense` (except carpentry.budget.balance)
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
            """
        
        # specific to budget balance
        if model == 'carpentry.budget.balance':
            sql += """
                    0.0 AS amount_expense,
                    0.0 AS amout_gain,
                    TRUE AS should_compute_gain,
                    FALSE AS should_value
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
