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
    phase_id = fields.Many2one(
        comodel_name='carpentry.group.phase',
        string='Phase',
        readonly=True,
    )
    launch_id = fields.Many2one(
        comodel_name='carpentry.group.launch',
        string='Launch',
        readonly=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Budget type',
        readonly=True,
    )
    # model
    group_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Group',
        readonly=True,
    )
    group_res_model = fields.Char(
        related='group_model_id.model',
    )
    # affectation
    quantity_affected = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
        group_operator='sum',
        readonly=True,
        help='Number of affected positions'
    )
    # budget
    budget_type = fields.Selection(
        string='Budget category',
        selection=lambda self: self.env['account.analytic.account'].fields_get()['budget_type']['selection'],
        readonly=True,
    )
    amount = fields.Float(
        string='Unitary amount',
        readonly=True,
    )
    subtotal = fields.Float(
        # amount * quantity_affected
        string='Budget',
        readonly=True,
    )


    #===== View build =====#
    def _get_queries_models(self):
        return ('project.project', 'carpentry.group.phase', 'carpentry.group.launch')
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        self._cr.execute("""
            CREATE or REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER (ORDER BY id_origin) AS id,
                    *
                FROM (
                    (%s)
                ) AS result
            )""", (
                AsIs(self._table),
                AsIs(') UNION ALL (' . join(self._get_queries()))
            )
        )
    
    def _get_queries(self):
        return (
            self._init_query(model)
            for model in self._get_queries_models()
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
                project.id AS id_origin,

                -- project & carpentry group
            	project.id AS project_id,
            	NULL AS launch_id,
            	NULL AS phase_id,

                -- model
                (SELECT id FROM ir_model WHERE model = 'project.project') AS group_model_id,

                -- affectation: position & qty affected
                NULL AS position_id,
                NULL AS quantity_affected,

                -- budget
                CASE
                    WHEN budget.type = 'amount'
                    THEN budget.balance
                    ELSE budget.qty_balance
                END AS amount,
                CASE
                    WHEN budget.type = 'amount'
                    THEN budget.balance
                    ELSE budget.qty_balance
                END AS subtotal,
                budget.analytic_account_id,
                budget.budget_type
            
        """ if model == 'project.project' else f"""

            SELECT
                affectation.id AS id_origin,

                -- project & carpentry group
                affectation.project_id,
            	CASE
                    WHEN '{model}' = 'carpentry.group.launch'
                    THEN carpentry_group.id
                    ELSE NULL
                END AS launch_id,
            	CASE
                    WHEN '{model}' = 'carpentry.group.phase'
                    THEN carpentry_group.id
                    ELSE NULL
                END AS phase_id,

                -- model
                affectation.group_model_id AS group_model_id,
                
                -- affectation: position & qty affected
                affectation.position_id,
                affectation.quantity_affected,

                -- budget
                budget.amount,
                affectation.quantity_affected * budget.amount AS subtotal,
                budget.analytic_account_id,
                budget.budget_type

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
            
        """ if model == 'project.project' else f"""

            INNER JOIN ir_model AS ir_model_group
                ON ir_model_group.id = affectation.group_model_id

            INNER JOIN carpentry_position_budget AS budget
                ON budget.position_id = affectation.position_id
            INNER JOIN {model.replace('.', '_')} AS carpentry_group
                ON carpentry_group.id = affectation.group_id
        """
    
    def _where(self, model):
        return """
            WHERE
                budget.balance != 0 AND
                is_computed_carpentry IS FALSE
            
            """ if model == 'project.project' else f"""

            WHERE
                quantity_affected != 0 AND
                ir_model_group.model = '{model}'
            """
    
    def _groupby(self, model):
        return ''
    
    def _orderby(self, model):
        return ''
    
    #===== Button =====#
    def open_position_budget(self, position_id=None):
        """ Open document providing budget (position or project) """
        position_id_ = position_id.id if position_id else self.position_id.id

        if not position_id_:
            return self.project_id.button_open_budget_lines()
        else:
            return self.env['ir.actions.act_window']._for_xml_id(
                'carpentry_position_budget.action_open_position_budget_add'
            ) | {
                'domain': [('position_id', '=', position_id_)],
                'context': {'default_position_id': position_id_},
            }
