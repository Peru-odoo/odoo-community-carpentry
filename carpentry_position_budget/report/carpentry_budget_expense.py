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
    position_id = fields.Many2one(store=False)
    launch_id = fields.Many2one(store=False)
    amount_subtotal = fields.Float(store=False)

    #===== View build =====#
    def _get_queries_models(self):
        """ Inherited in sub-modules (purchase, mrp, timesheet) """
        return ('carpentry.budget.reservation',)
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        queries = self._get_queries()
        if queries:
            budget_types = self.env['account.analytic.account']._get_budget_type_workforce()
            self._cr.execute("""
                CREATE or REPLACE VIEW %(view_name)s AS (
                    SELECT
                        row_number() OVER (ORDER BY
                            expense.record_id,
                            expense.record_model_id,
                            expense.analytic_account_id
                        ) AS id,
                        expense.project_id,
                        expense.date,
                        expense.active,
                        
                        expense.record_id,
                        expense.record_model_id,
                        %(sql_record_fields)s
                        expense.analytic_account_id,
                        expense.budget_type,
                        hourly_cost.coef AS hourly_cost_coef, -- for `carpentry.budget.expense.distributed`
                        
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
                            WHEN expense.budget_type IN %(budget_types)s AND 'DEVALUE' = ANY(ARRAY_AGG(value_or_devalue_workforce_expense))
                            THEN CASE
                                WHEN COALESCE(hourly_cost.coef, 0.0) != 0.0
                                THEN 1 / hourly_cost.coef
                                ELSE 0.0
                            END ELSE 1.0
                        END AS amount_expense,
                        
                        -- expense valued: computed from `amount_expense` if NULL, and valued from it if needed
                        CASE 
                            WHEN TRUE = ANY(ARRAY_AGG(amount_expense_valued IS NULL)) -- if need computation from `amount_expense`
                            THEN SUM(expense.amount_expense) *
                                CASE
                                    WHEN expense.budget_type IN %(budget_types)s AND 'VALUE' = ANY(ARRAY_AGG(value_or_devalue_workforce_expense))
                                    THEN hourly_cost.coef
                                    ELSE 1.0
                                END
                            ELSE SUM(expense.amount_expense_valued)
                        END AS amount_expense_valued,
                        
                        -- gain
                        COALESCE(SUM(expense.amount_reserved) * (
                            CASE
                                WHEN expense.budget_type IN %(budget_types)s
                                THEN hourly_cost.coef
                                ELSE 1.0
                            END
                        ), 0.0)
                        - COALESCE(CASE
                            WHEN TRUE = ANY(ARRAY_AGG(amount_expense_valued IS NULL)) -- if need computation from `amount_expense`
                            THEN SUM(expense.amount_expense) *
                                CASE
                                    WHEN expense.budget_type IN %(budget_types)s AND 'VALUE' = ANY(ARRAY_AGG(value_or_devalue_workforce_expense))
                                    THEN hourly_cost.coef
                                    ELSE 1.0
                                END
                            ELSE SUM(expense.amount_expense_valued)
                        END, 0.0) AS amount_gain
                    
                    FROM (
                        (%(union)s)
                    ) AS expense
                    
                    -- for (h) to (€) (de)valuation when needed (on PO: € -> h)
                    LEFT JOIN carpentry_budget_hourly_cost AS hourly_cost
                        ON  hourly_cost.project_id = expense.project_id
                        AND hourly_cost.analytic_account_id = expense.analytic_account_id
                        AND expense.budget_type IN %(budget_types)s
                    
                    GROUP BY
                        expense.project_id,
                        expense.date,
                        expense.active,
                        expense.record_id,
                        expense.record_model_id,
                        expense.analytic_account_id,
                        expense.budget_type,
                        hourly_cost.coef
                    ORDER BY
                        expense.record_id
                )""", {
                    'view_name': AsIs(self._table),
                    'sql_record_fields': AsIs(self._get_sql_record_fields_main_view('expense.')),
                    'budget_types': tuple(budget_types),
                    'union': AsIs(') UNION ALL (' . join(queries)),
            })
    
    def _get_sql_record_fields_main_view(self, view=''):
        """ SQL for balance_id, purchase_id, production_id, task_id, ... """
        Reservation = self.env['carpentry.budget.reservation']
        sql_record_fields = ''
        for field in Reservation._get_record_fields():
            model = Reservation[field]._name
            if model == 'carpentry.budget.balance':
                model_id = f"(SELECT id FROM ir_model WHERE model = '{model}')"
            else:
                model_id = self.env['ir.model']._get_id(model)
            
            sql_record_fields += f"""
                CASE
                    WHEN {view}record_model_id = {model_id}
                    THEN {view}record_id
                    ELSE NULL
                END AS {field},
            """
        return sql_record_fields

    def _select(self, model, models):
        if model == 'carpentry.budget.reservation':
            Reservation = self.env['carpentry.budget.reservation']
            record_fields = Reservation._get_record_fields()
            
            sql_record_model_id = ''
            for record_field in record_fields:
                model = Reservation[record_field]._name
                if model == 'carpentry.budget.balance':
                    model_id = f"(SELECT id FROM ir_model WHERE model = '{model}')"
                else:
                    model_id = self.env['ir.model']._get_id(model)
                
                sql_record_model_id += f"""
                    CASE
                        WHEN {record_field} IS NOT NULL
                        THEN {model_id}
                        ELSE
                """
            sql_record_model_id += ' NULL ' + ' END ' * len(record_fields)

            sql = f"""
                SELECT
                    project_id,
                    date,
                    active AS active,
                    COALESCE({', ' . join (record_fields)}) AS record_id,
                    {sql_record_model_id} AS record_model_id,
                    analytic_account_id,
                    budget_type,

                    amount_reserved,

                    NULL AS value_or_devalue_workforce_expense,
                    0.0 AS amount_expense,
                    0.0 AS amount_expense_valued
            """
        
        return sql

    def _from(self, model, models):
        if model == 'carpentry.budget.reservation':
            return "FROM carpentry_budget_reservation AS reservation"
        else:
            return f"FROM {model.replace('.', '_')} AS record"

    def _join(self, model, models):
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
            return 'WHERE TRUE'
        else:
            return 'WHERE analytic.budget_type IS NOT NULL'
    
    def _groupby(self, model, models):
        if model == 'carpentry.budget.reservation':
            return ''
        else:
            return 'GROUP BY analytic.budget_type, analytic.id, record.id, record.project_id'
    
    def _orderby(self, model, models):
        return ''

    def _having(self, model, models):
        return ''

    #===== Compute =====#
    @api.depends('record_model_id')
    def _compute_launch_ids(self):
        for expense in self:
            expense.launch_ids = (
                expense.record_ref and
                'launch_ids' in expense.record_ref and # for position, launch_ids does not exist
                expense.record_ref.launch_ids
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
                        record_id,
                        record_model_id,
                        analytic_account_id
                    ) AS id,
                    project_id,
                    active,
                    
                    record_id,
                    record_model_id,
                    %(sql_record_fields)s
                    analytic_account_id,
                    budget_type,
                    -- AVG(hourly_cost_coef) AS hourly_cost_coef, -- for `carpentry.budget.expense.distributed`
                    
                    SUM(amount_reserved) AS amount_reserved,
                    SUM(amount_reserved_valued) AS amount_reserved_valued,
                    SUM(amount_expense) AS amount_expense,
                    SUM(amount_expense_valued) AS amount_expense_valued,
                    SUM(amount_gain) AS amount_gain
                
                FROM carpentry_budget_expense_history
                
                GROUP BY
                    project_id,
                    record_id,
                    record_model_id,
                    analytic_account_id,
                    budget_type,
                    active
            )""", {
                'view_name': AsIs(self._table),
                'sql_record_fields': AsIs(self._get_sql_record_fields_main_view())
            }
        )
