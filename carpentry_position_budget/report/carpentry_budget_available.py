# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command, tools, exceptions
from odoo.osv import expression
from collections import defaultdict

class CarpentryBudgetAvailable(models.Model):
    """ Union of `carpentry.position.budget` and `account.move.budget.line`
        for report of initially available budget, aka *`Where does the budget comes from?*
    """
    _name = 'carpentry.budget.available'
    _description = 'Available budget report'
    _auto = False
    _order = 'seq_group, seq_analytic_account'

    #===== Fields methods =====#
    def _selection_group_res_model(self):
        return [
            ('carpentry.group.phase', 'Phase'),
            ('carpentry.group.launch', 'Launch'),
            ('project.project', 'Project'),
        ]
    
    #===== Fields =====#
    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Project'
    )
    position_id = fields.Many2one(
        comodel_name='carpentry.position',
        string='Position',
    )

    # affectation
    # group coming from `carpentry.group.affectation` are either a phase or a launch
    # group coming from `account.move.budget.line` is a project
    group_id = fields.Many2oneReference( # actually an `Integer` field, so not .dot notation
        model_field='group_res_model',
        string='Group ID',
        readonly=True,
        required=True,
        index='btree_not_null',
    )
    group_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Group Model ID',
        ondelete='cascade'
    )
    group_res_model = fields.Char(
        string='Group Model',
    )
    group_ref = fields.Reference(
        selection='_selection_group_res_model',
    )
    seq_group = fields.Integer()
    quantity_affected = fields.Float(
        string="Position's affected quantity",
        digits='Product Unit of Measure',
        group_operator='sum'
    )

    # budget
    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Budget',
    )
    budget_type = fields.Selection(
        string='Budget type',
        selection=lambda self: self.env['account.analytic.account'].fields_get()['budget_type']['selection'],
    )
    amount = fields.Float(
        string='Unitary Amount',
    )
    subtotal = fields.Float(
        # amount * quantity_affected
        string='Subtotal',
    )
    seq_analytic_account = fields.Integer()


    #===== View build =====#
    def init(self):
        query_affectation = self._init_query('affectation')
        query_project = self._init_query('project')

        tools.drop_view_if_exists(self.env.cr, self._table)
        
        self._cr.execute("""
            CREATE or REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER (ORDER BY group_model_id, group_id, analytic_account_id) AS id,
                    *
                FROM (
                    (%s)
                    UNION ALL
                    (%s)
                ) AS result
            )""", (
                self._table,
                query_affectation,
                query_project
            )
        )
    
    def _init_query(self, model):
        return """
            {where}
            {fromtable}
            {join}
            {where}
            {groupby}
            {orderby}
        """ . format(
            where=self._select(model),
            fromtable=self._from(model),
            join=self._join(model),
            where=self._where(model),
            groupby=self._groupby(model),
            orderby=self._orderby(model),
        )

    def _select(self, model):
        return """
            SELECT
                affectation.project_id,
                
                -- affectation: phase or launch
                affectation.group_id,
                affectation.group_model_id,
                affectation.seq_group,
                ir_model_group.model AS group_res_model,
                ir_model_group.model || ',' || affectation.group_id AS group_ref,

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
        return """
	        FROM
                carpentry_group_affectation AS affectation
        """

    def _join(self, model):
        return """
            INNER JOIN ir_model AS ir_model_group
                ON ir_model_group.id = affectation.group_model_id
            INNER JOIN carpentry_position_budget AS budget
                ON budget.position_id = affectation.position_id
            INNER JOIN account_analytic_account AS analytic
                ON analytic.id = budget.analytic_account_id
        """
    
    def _where(self, model):
        return """
            WHERE
                quantity_affected != 0
        """
    
    def _groupby(self, model):
        return ''
    
    def _orderby(self, model):
        return ''
    