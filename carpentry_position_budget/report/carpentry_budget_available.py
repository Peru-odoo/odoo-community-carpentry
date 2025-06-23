# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api
from psycopg2.extensions import AsIs

class CarpentryBudgetAvailable(models.Model):
    """ Union of:
        - phase & launch budgets (carpentry.group.affectation) and
        - project budgets (account.move.budget.line)
        for report of *Initially available budget*,
                   aka *Where does the budget comes from?*
    """
    _name = 'carpentry.budget.available'
    _description = 'Project & launches budgets'
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
    launch_id = fields.Many2one(
        comodel_name='carpentry.group.launch',
        string='Launch',
        readonly=True,
    )
    phase_id = fields.Many2one(
        comodel_name='carpentry.group.phase',
        string='Phase',
        readonly=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Budget type',
        readonly=True,
    )
    # affectation
    quantity_affected = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
        group_operator='sum',
        readonly=True,
        help='Number of affected positions',
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
    # model
    group_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Group',
        readonly=True,
    )
    group_res_model = fields.Char(
        related='group_model_id.model',
    )

    #===== View build =====#
    def _get_queries_models(self):
        return ('project.project', 'carpentry.group.phase', 'carpentry.group.launch', 'carpentry.position')
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        queries = self._get_queries()
        if queries:
            self._cr.execute("""
                CREATE or REPLACE VIEW %s AS (
                    SELECT
                        row_number() OVER (ORDER BY unique_key) AS id,
                        *
                    FROM (
                        (%s)
                    ) AS result
                )""", (
                    AsIs(self._table),
                    AsIs(') UNION ALL (' . join(queries))
                )
            )
    
    def _get_queries(self):
        return (
            self._init_query(model)
            for model in self._get_queries_models()
        )
    
    def _init_query(self, model):
        models = {x.model: x.id for x in self.env['ir.model'].sudo().search([])}

        return """
            {select}
            {from_table}
            {join}
            {where}
            {groupby}
            {orderby}
        """ . format(
            select=self._select(model, models),
            from_table=self._from(model, models),
            join=self._join(model, models),
            where=self._where(model, models),
            groupby=self._groupby(model, models),
            orderby=self._orderby(model, models),
        )

    def _select(self, model, models):
        if model == 'project.project':
            return f"""
                SELECT
                    'project-' || budget_project.id AS unique_key,

                    -- project & carpentry group
                    project.id AS project_id,
                    NULL AS launch_id,
                    NULL AS phase_id,
                    {models['project.project']} AS group_model_id,

                    -- affectation: position & qty affected
                    NULL AS position_id,
                    NULL AS quantity_affected,

                    -- budget
                    CASE
                        WHEN budget_project.type = 'amount'
                        THEN budget_project.balance
                        ELSE budget_project.qty_balance
                    END AS amount,
                    CASE
                        WHEN budget_project.type = 'amount'
                        THEN budget_project.balance
                        ELSE budget_project.qty_balance
                    END AS subtotal,
                    budget_project.analytic_account_id,
                    budget_project.budget_type
                
            """

        else:
            shortname = model.replace('carpentry.group.', '').replace('.group', '')
            return f"""
                SELECT
                    '{shortname}-' || carpentry_group.id || '-' || budget.id AS unique_key,

                    -- project_id, launch_id, phase_id
                    carpentry_group.project_id,
                    {'carpentry_group.id' if model == 'carpentry.group.launch' else 'NULL::integer'} AS launch_id,
                    {'carpentry_group.id' if model == 'carpentry.group.phase'  else 'NULL::integer'} AS phase_id,
                    {models[model]} AS group_model_id,

                    -- affectation: position & qty affected
                    budget.position_id,
                    {
                        'SUM(carpentry_group.quantity)'
                        if model == 'carpentry.position'
                        else 'SUM(affectation.quantity_affected)'
                    } AS quantity_affected,

                    -- budget
                    SUM(budget.amount) AS amount,
                    {
                        'SUM(budget.amount)'
                        if model == 'carpentry.position'
                        else 'SUM(affectation.quantity_affected * budget.amount)'
                    } AS subtotal,

                    budget.analytic_account_id,
                    budget.budget_type
            """

    def _from(self, model, models):
        if model == 'project.project':
            return 'FROM account_move_budget_line AS budget_project'
        elif model == 'carpentry.position':
            return 'FROM carpentry_position AS carpentry_group'
        else:
            return 'FROM carpentry_group_affectation AS affectation'

    def _join(self, model, models):
        if model == 'project.project':
            return """
                INNER JOIN project_project AS project
                    ON project.id = budget_project.project_id
            """
        elif model in ['carpentry.group.phase', 'carpentry.group.launch']:
            return f"""
                INNER JOIN carpentry_position_budget AS budget
                    ON budget.position_id = affectation.position_id
                INNER JOIN {model.replace('.', '_')} AS carpentry_group
                    ON carpentry_group.id = affectation.group_id
            """
        elif model == 'carpentry.position':
            return """
                INNER JOIN carpentry_position_budget AS budget
                    ON budget.position_id = carpentry_group.id
            """
    
    def _where(self, model, models):
        if model == 'project.project':
            return """
                WHERE
                    budget_project.balance != 0 AND
                    is_computed_carpentry IS FALSE
                
                """

        elif model in ('carpentry.group.phase', 'carpentry.group.launch'):
            return f"""
                WHERE
                    affectation.active IS TRUE AND
                    quantity_affected != 0 AND
                    affectation.group_model_id = {models[model]}
                """

        elif model == 'carpentry.position':
            return """
                WHERE
                    carpentry_group.active IS TRUE
            """
    
    def _groupby(self, model, models):
        return '' if model == 'project.project' else """

            GROUP BY 
               carpentry_group.project_id,
               carpentry_group.id,
               budget.id,
               budget.position_id,
               budget.budget_type,
               budget.analytic_account_id
        """
    
    def _orderby(self, model, models):
        return ''
    
    #===== Queries =====#
    def _get_groupby(self, records, launch_ids_, groupby):
        return {}
        # rg_result = self.read_group(
        #     domain=[('launch_id', 'in', launch_ids_), (groupby, 'in', records.mapped(groupby))],
        #     fields=['subtotal:sum'],
        #     groupby=[groupby],
        # )
        # many2one = self[groupby]!!._fields['aaa']
        # return {
        #     x[groupby][0] if many2one else x[groupby]: x['subtotal']
        #     for x in rg_result
        # }



    #===== ORM method =====#
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ Add position's `quantity_affected` in position's `display_name`
            when grouping per position
        """
        res = super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)
        
        if (
            res and 'position_id' in res[0] and # groupby by `position_id`
            self._context.get('display_model_shortname') # not programatic call
        ):
            # count position's affected quantities per launch
            position_ids_ = [x['position_id'][0] for x in res if x.get('position_id')]
            rg_result = self.env['carpentry.group.affectation'].read_group(
                domain=[('group_res_model', '=', 'carpentry.group.launch'), ('position_id', 'in', position_ids_)],
                fields=['quantity_affected:sum'],
                groupby=['group_id', 'position_id'],
                lazy=False,
            )
            mapped_quantities = {
                # (launch_id, position_id): qty:sum
                (x['group_id'], x['position_id'][0]): x['quantity_affected']
                for x in rg_result
            }

            # add the count in position's display_name
            launch_id_ctx_ = (
                # when not grouping per launch, but pivot view on a single launch
                self._context.get('active_model') == 'carpentry.group.launch' and
                self._context.get('active_id')
            )
            for data in res:
                launch_id_ = launch_id_ctx_ or data.get('launch_id') and data['launch_id'][0]
                position = data.get('position_id')
                if launch_id_ and position:
                    display_name = '{} ({})' . format(
                        position[1],
                        round(mapped_quantities.get((launch_id_, position[0]), 0.0))
                    )
                    data['position_id'] = (position[0], display_name)
        
        return res

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
