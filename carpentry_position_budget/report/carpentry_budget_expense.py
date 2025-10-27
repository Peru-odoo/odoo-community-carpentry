# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from psycopg2.extensions import AsIs


class CarpentryBudgetExpenseHistory(models.Model):
    """ Should be overriden in each Carpentry module with expense
        With `date` field
    """
    _name = 'carpentry.budget.expense.history'
    _inherit = ['carpentry.budget.remaining']
    _description = 'Expenses History'
    _auto = False

    #===== Fields =====#
    currency_id = fields.Many2one(
        related='project_id.currency_id',
    )
    date = fields.Date(
        string='Date',
        readonly=True,
    )
    launch_ids = fields.Many2many(
        string='Launchs',
        comodel_name='carpentry.group.launch',
        compute='_compute_launch_ids',
    )
    amount_reserved = fields.Float(
        string='Reserved budget (brut)',
    )
    amount_reserved_valued = fields.Monetary(
        string='Reserved budget',
        readonly=True,
    )
    amount_expense = fields.Float(
        string='Real expense (brut)',
        digits='Product Unit of Measure',
        readonly=True,
    )
    amount_expense_valued = fields.Monetary(
        string='Real expense',
        readonly=True,
    )
    amount_gain = fields.Monetary(
        string='Gain or Loss',
        readonly=True,
        help='Budget reservation - Real expense',
    )

    # cancel fields
    state = fields.Selection(store=False)
    launch_id = fields.Many2one(store=False)
    group_model_id = fields.Many2one(store=False)
    group_res_model = fields.Char(related='', store=False)
    amount_subtotal = fields.Float(store=False)

    #===== View build =====#
    def _get_queries_models(self):
        """ Inherited in sub-modules (purchase, mrp, timesheet) """
        return ('carpentry.budget.reservation', 'carpentry.budget.balance',)
    
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
                        expense.project_id,
                        expense.date,
                        expense.active,
                        
                        expense.section_id,
                        expense.section_model_id,
                        expense.analytic_account_id,
                        expense.budget_type,
                        
                        -- reserved budget
                        SUM(expense.amount_reserved) AS amount_reserved,
                        SUM(expense.amount_reserved) * (
                            CASE
                                WHEN expense.budget_type IN %(budget_types)s
                                THEN hourly_cost.coef
                                ELSE 1.0
                            END
                        ) AS amount_reserved_valued,
                        
                        -- expense
                        SUM(expense.amount_expense) *
                        CASE
                            WHEN expense.budget_type IN %(budget_types)s AND TRUE = ANY(ARRAY_AGG(should_devalue_workforce_expense))
                            THEN CASE
                                WHEN COUNT(hourly_cost.coef) > 0 AND hourly_cost.coef != 0.0
                                THEN 1 / hourly_cost.coef
                                ELSE 0.0
                            END ELSE 1.0
                        END AS amount_expense,
                        SUM(expense.amount_expense_valued) AS amount_expense_valued,
                        
                        -- gain
                        SUM(amount_reserved) * (
                            CASE
                                WHEN expense.budget_type IN %(budget_types)s
                                THEN hourly_cost.coef
                                ELSE 1.0
                            END
                        ) - SUM(amount_expense_valued) AS amount_gain
                    
                    FROM (
                        (%(union)s)
                    ) AS expense
                    
                    -- for (h) to (€) valuation when needed (on PO)
                    LEFT JOIN carpentry_budget_hourly_cost AS hourly_cost
                        ON  hourly_cost.project_id = expense.project_id
                        AND hourly_cost.analytic_account_id = expense.analytic_account_id
                    
                    GROUP BY
                        expense.project_id,
                        expense.date,
                        expense.active,
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

    def _select(self, model, models):
        if model == 'carpentry.budget.reservation':
            sql = """
                SELECT
                    reservation.project_id,
                    reservation.date,
                    reservation.active,
                    reservation.section_id AS section_id,
                    reservation.section_model_id,
                    reservation.analytic_account_id,
                    reservation.budget_type,
                    
                    reservation.amount_reserved,
                    FALSE AS should_devalue_workforce_expense,

                    0.0 AS amount_expense,
                    0.0 AS amount_expense_valued
            """
        elif model == 'carpentry.budget.balance':
            sql = f"""
                SELECT
                    section.project_id,
                    section.date_budget AS date,
                    TRUE as active,
                    section.id AS section_id,
                    (SELECT id FROM ir_model WHERE model = '{model}') AS section_model_id,
                    analytic.id AS analytic_account_id,
                    analytic.budget_type,

                    0.0 AS amount_reserved,
                    FALSE AS should_devalue_workforce_expense,

                    0.0 AS amount_expense,
                    0.0 AS amount_expense_valued
            """
        
        return sql

    def _from(self, model, models):
        if model == 'carpentry.budget.reservation':
            return 'FROM carpentry_budget_reservation AS reservation'
        else:
            return f"FROM {model.replace('.', '_')} AS section"

    def _join(self, model, models):
        if model == 'carpentry.budget.reservation':
            return """
                INNER JOIN ir_model AS model
                    ON model.id = reservation.section_model_id
            """
        elif model == 'carpentry.budget.balance':
            return """
                INNER JOIN carpentry_budget_reservation AS reservation
                    ON reservation.section_id = section.id
                    AND reservation.section_model_id = section_model_id
                
                INNER JOIN account_analytic_account AS analytic
                    ON analytic.id = reservation.analytic_account_id
            """
        else:
            return ''

    def _join_product_analytic_distribution(self):
        return """
            INNER JOIN product_product
                ON product_product.id = line.product_id
            INNER JOIN product_template
                ON product_template.id = product_product.product_tmpl_id
            
            LEFT JOIN LATERAL
                jsonb_each_text(line.analytic_distribution)
                AS analytic_distribution (aac_id, percentage)
                ON true

            -- analytic
            LEFT JOIN account_analytic_account AS analytic
                ON analytic.id = analytic_distribution.aac_id::integer
        """
    
    def _where(self, model, models):
        if model == 'carpentry.budget.reservation':
            return ''
        
        return 'WHERE analytic.budget_type IS NOT NULL'
    
    def _groupby(self, model, models):
        if model == 'carpentry.budget.reservation':
            return ''
        
        return 'GROUP BY analytic.budget_type, analytic.id, section.id, section.project_id'
    
    def _orderby(self, model, models):
        return ''

    def _having(self, model, models):
        return ''

    #===== Compute =====#
    @api.depends('section_id', 'section_model_id')
    def _compute_launch_ids(self):
        for expense in self:
            expense.launch_ids = (
                expense.section_ref and
                'launch_ids' in expense.section_ref and # for position, launch_ids does not exist
                expense.section_ref.launch_ids
            )

class CarpentryBudgetExpense(models.Model):
    """ *Not* grouped by date (without history): for *Loss/Gains* report """
    _name = 'carpentry.budget.expense'
    _inherit = ['carpentry.budget.expense.history']
    _description = 'Expenses'
    _auto = False

    date = fields.Date(store=False)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        self._cr.execute("""
            CREATE or REPLACE VIEW %(view_name)s AS (
                SELECT
                    row_number() OVER (ORDER BY
                        section_id,
                        section_model_id,
                        analytic_account_id
                    ) AS id,
                    project_id,
                    active,
                    
                    section_id,
                    section_model_id,
                    analytic_account_id,
                    budget_type,
                    
                    SUM(amount_reserved) AS amount_reserved,
                    SUM(amount_reserved_valued) AS amount_reserved_valued,
                    SUM(amount_expense) AS amount_expense,
                    SUM(amount_expense_valued) AS amount_expense_valued,
                    SUM(amount_gain) AS amount_gain
                
                FROM carpentry_budget_expense_history
                
                GROUP BY
                    project_id,
                    section_id,
                    section_model_id,
                    analytic_account_id,
                    budget_type,
                    active
            )""", {
                'view_name': AsIs(self._table),
            }
        )

