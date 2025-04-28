# -*- coding: utf-8 -*-

from odoo import models, fields, tools, _, api
from psycopg2.extensions import AsIs

class CarpentryBudgetAvailable(models.Model):
    """ Union of `carpentry.position.budget` and `account.move.budget.line`
        for report of initially available budget, aka *`Where does the budget comes from?*
    """
    _name = 'carpentry.budget.available'
    _description = 'Available budget report'
    _auto = False
    _order = 'group_res_model_name DESC, seq_group, seq_analytic_account'

    #===== Fields =====#
    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Project',
        readonly=True,
    )
    position_id = fields.Many2one(
        comodel_name='carpentry.position',
        string='Position',
        readonly=True,
    )

    # affectation
    # group coming from `carpentry.group.affectation` are either a phase or a launch
    # group coming from `account.move.budget.line` is a project
    display_name = fields.Char(
        string='Group',
        readonly=True,
    )
    group_res_model = fields.Char(
        string='Group Model',
        readonly=True,
    )
    group_res_model_name = fields.Char(
        string='Model Name',
        readonly=True,
    )
    seq_group = fields.Integer(
        readonly=True,
    )
    quantity_affected = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
        group_operator='sum',
        readonly=True,
        help='Number of affected positions'
    )

    # budget
    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Budget',
        readonly=True,
    )
    budget_type = fields.Selection(
        string='Budget type',
        selection=lambda self: self.env['account.analytic.account'].fields_get()['budget_type']['selection'],
        readonly=True,
    )
    amount = fields.Float(
        string='Unitary Amount',
        readonly=True,
    )
    subtotal = fields.Float(
        # amount * quantity_affected
        string='Subtotal',
        readonly=True,
    )
    seq_analytic_account = fields.Integer(
        readonly=True,
    )


    #===== View build =====#
    def init(self):
        queries = (
            self._init_query('project.project'),
            self._init_query('carpentry.group.phase'),
            self._init_query('carpentry.group.launch'),
        )

        tools.drop_view_if_exists(self.env.cr, self._table)
        
        self._cr.execute("""
            CREATE or REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER (ORDER BY seq_group, seq_analytic_account) AS id,
                    *
                FROM (
                    (%s)
                ) AS result
            )""", (
                AsIs(self._table),
                AsIs(') UNION ALL (' . join(queries))
            )
        )
    
    def _init_query(self, model):
        return """
            {select}
            {from_table}
            {join}
            {where}
            {groupby}
            {orderby}
        """ . format(
            select=self._select(model),
            from_table=self._from(model),
            join=self._join(model),
            where=self._where(model),
            groupby=self._groupby(model),
            orderby=self._orderby(model),
        )

    def _select(self, model):
        return f"""
            SELECT
                -- project
            	project.id AS project_id,

                -- model
                '{_("Global budget")}' AS display_name,
                -1 AS seq_group,
                '{model}' AS group_res_model,
                '{_('Project')}' AS group_res_model_name,

                -- affectation: position & qty affected
                NULL AS position_id,
                NULL AS quantity_affected,

                -- budget
                budget.balance AS amount,
                budget.balance AS subtotal,
                budget.analytic_account_id,
                budget.budget_type,
                analytic.sequence AS seq_analytic_account
            
        """ if model == 'project.project' else f"""

            SELECT
                affectation.project_id,
                
                -- affectation
                carpentry_group.name AS display_name,
                carpentry_group.sequence AS seq_group,

                -- model
                '{model}' AS group_res_model,
                '{_(self.env[model]._description)}' AS group_res_model_name,
                

                -- affectation: position & qty affected
                affectation.position_id,
                affectation.quantity_affected,

                -- budget
                budget.amount,
                affectation.quantity_affected * budget.amount AS subtotal,
                budget.analytic_account_id,
                budget.budget_type,
                analytic.sequence AS seq_analytic_account

        """

    def _from(self, model):
        return (
            'FROM account_move_budget_line AS budget'

            if model == 'project.project' else
	        
            'FROM carpentry_group_affectation AS affectation'
        )

    def _join(self, model):
        return """
            INNER JOIN project_project AS project
                ON project.id = budget.project_id
            INNER JOIN account_analytic_account AS analytic
                ON analytic.id = budget.analytic_account_id
            
        """ if model == 'project.project' else f"""

            INNER JOIN ir_model AS ir_model_group
                ON ir_model_group.id = affectation.group_model_id

            INNER JOIN carpentry_position_budget AS budget
                ON budget.position_id = affectation.position_id
            INNER JOIN account_analytic_account AS analytic
                ON analytic.id = budget.analytic_account_id
            INNER JOIN {model.replace('.', '_')} AS carpentry_group
                ON carpentry_group.id = affectation.group_id
        """
    
    def _where(self, model):
        return (
            ''
            
            if model == 'project.project' else f"""

            WHERE
                quantity_affected != 0 AND
                ir_model_group.model = '{model}'
            """
        )
    
    def _groupby(self, model):
        return ''
    
    def _orderby(self, model):
        return ''
    

    #===== ORM overwrite =====#
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ Forces specific `orderby` """
        orderby = self._order
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)
