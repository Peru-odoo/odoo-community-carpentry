# -*- coding: utf-8 -*-

from odoo import models, fields, tools, _, api, exceptions
from psycopg2.extensions import AsIs

class CarpentryBudgetRemaining(models.Model):
    """ Union of (+) `carpentry.budget.available` and
                 (-) `carpentry.budget.reservation`
    """
    _name = 'carpentry.budget.remaining'
    _inherit = ['carpentry.budget.available']
    _description = 'Project & launches remaining budgets'
    _auto = False

    #===== Fields =====#
    state = fields.Selection(
        selection=[('budget', 'Budget'), ('reservation', 'Reservation')],
        string='State',
        readonly=True,
    )
    amount_subtotal = fields.Float(
        string='Remaining',
    )
    # records
    balance_id = fields.Many2one(
        comodel_name='carpentry.budget.balance',
        string='Balance',
        readonly=True,
    )
    # models
    record_id = fields.Many2oneReference(
        string='Record ID',
        model_field='record_res_model',
        readonly=True,
    )
    record_ref = fields.Reference(
        string='Name',
        selection='_selection_record_ref',
        compute='_compute_record_ref',
        readonly=True,
    )
    # fields cancelling (necessary so they are not in SQL from ORM)
    phase_id = fields.Many2one(store=False)
    position_id = fields.Many2one(store=False)
    amount_unitary = fields.Float(store=False)
    quantity_affected = fields.Float(store=False)

    #===== View build =====#
    def _get_queries_models(self):
        return ('carpentry.budget.reservation', 'carpentry.budget.available')

    def init(self):
        """ Over-write `init` of `carpentry.budget.available`
            to make it simplier
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        queries = self._get_queries()
        if queries:
            # SELECT SQL for balance_id, purchase_id, production_id, task_id, ...
            Reservation = self.env['carpentry.budget.reservation']
            sql_record_fields = ''
            for field in Reservation._get_record_fields():
                model = Reservation[field]._name
                sql_record_fields += f"""
                    CASE
                        WHEN expense.record_model_id = '{model}'
                        THEN expense.record_id
                        ELSE NULL
                    END AS {field}
                """

            self._cr.execute(f"""
                CREATE or REPLACE VIEW %s AS (
                    SELECT
                        row_number() OVER (ORDER BY unique_key) AS id,
                        state,
                        
                        project_id,
                        launch_id,
                        active,

                        analytic_account_id,
                        amount_subtotal,
                        budget_type,
                        
                        record_model_id,
                        record_id
                    FROM (
                        (%s)
                    ) AS result
                )""", (
                    AsIs(self._table),
                    AsIs(') UNION ALL (' . join(queries))
                )
            )

    def _select(self, model, models):
        # SQL for balance_id, purchase_id, production_id, task_id, ...
        Reservation = self.env['carpentry.budget.reservation']
        record_fields = Reservation._get_record_fields()
        prefix = 'NULL AS ' if model == 'carpentry.budget.available' else 'reservation.'
        sql_record_fields = ', ' . join([prefix + field for field in record_fields])

        if model == 'carpentry.budget.available':
            return f"""
                SELECT
                    'available-' || available.id AS unique_key,
                    'budget' AS state,
                    
                    -- project & launch
                    available.project_id,
                    available.launch_id,
                    available.active,

                    -- budget
                    available.analytic_account_id,
                    available.amount_subtotal AS amount_subtotal,
                    available.amount_subtotal_valued AS amount_subtotal_valued,
                    available.budget_type,

                    -- record_id: position or project
                    available.record_model_id,
                    CASE
                        WHEN available.launch_id IS NOT NULL
                        THEN available.position_id
                        ELSE available.project_id
                    END AS record_id,
                    {sql_record_fields} -- balance_id, purchase_id, ...
            """
        else:
            sql_record_model_id = ''
            for field in record_fields:
                model = Reservation[field]._name
                if model == 'carpentry.budget.balance':
                    model_id = f"(SELECT id FROM ir_model WHERE model = '{model}')"
                else:
                    model_id = models[model]
                sql_record_model_id += f"""
                    CASE
                        WHEN reservation.{field} IS NOT NULL
                        THEN {model_id}
                        ELSE
                """
            if sql_record_model_id:
                sql_record_model_id += ' NULL ' + (' END ' * len(record_fields))
            
            return f"""
                SELECT
                    'reservation-' || reservation.id AS unique_key,
                    'reservation' AS state,

                    -- project & launch
                    reservation.project_id,
                    reservation.launch_id,
                    reservation.active,
                    
                    -- budget
                    reservation.analytic_account_id,
                    -1 * reservation.amount_reserved AS amount_subtotal,
                    NULL AS amount_subtotal_valued, -- never needed, don't do it
                    reservation.budget_type,

                    -- record
                    {sql_record_model_id} AS record_model_id,
                    COALESCE({', '.join(record_fields)}) AS record_id,
                    {sql_record_fields} -- balance_id, purchase_id, ...
            """

    def _from(self, model, models):
        return (
            'FROM carpentry_budget_available AS available'

            if model == 'carpentry.budget.available' else
	        
            'FROM carpentry_budget_reservation AS reservation'
        )

    def _join(self, model, models):
        return ''
    
    def _where(self, model, models):
        if model == 'carpentry.budget.available':
            return f"""
                -- no available budget only from project and launchs
                WHERE available.record_model_id IN (
                    {models['project.project']},
                    {models['carpentry.group.launch']}
                )
            """
        else:
            return "WHERE amount_reserved != 0.0"
    
    def _groupby(self, model, models):
        return ''
    
    def _orderby(self, model, models):
        return ''

    #===== Compute =====#
    @api.depends('record_id', 'record_model_id')
    def _compute_record_ref(self):
        for available in self:
            available.record_ref = (
                '{},{}' . format(
                    available.record_model_id.model,
                    available.record_id,
                )
                if available.record_model_id and available.record_id
                else False
            )
    
    #===== Actions & Buttons =====#
    def _get_raise_to_reservations(self, message):
        """ Used when trying to delete source of budget, like when:
            * deleting `carpentry.group.launch`
            * unaffecting `carpentry.affectation` (position-to-launch)

            :return: kwargs of `exceptions.RedirectWarning`
        """
        return {
            'message': message,
            'action': self.action_open_tree(),
            'button_text': _("Show reservations"),
        }
    def action_open_tree(self):
        """ :arg self: records of this model, gotten from a `search` """
        return (
            self.env['ir.actions.act_window']
            ._for_xml_id('carpentry_position_budget.action_open_budget_report_remaining')
        ) | {
            'name': _("Budget reservations"),
            'views': [(False, 'tree')],
            'domain': [('id', 'in', self.ids)],
        }
    
    def open_record_ref(self, reservation=None):
        if reservation:
            # see `carpentry.budget.reservation`
            self = reservation
        
        """ Opens a document providing or reserving some budget """
        if not self.record_model_id:
            return {}
        
        if self.record_ref and hasattr(self.record_ref, '_carpentry_budget_reservation'):
            # budget reservation
            return {
                'type': 'ir.actions.act_window',
                'name': self.record_ref._description,
                'res_model': self.record_ref._name,
                'res_id': self.record_ref.id,
                'view_mode': 'form',
            }
        
        elif self.record_model_id.model in ('carpentry.position', 'project.project'):
            # available budget
            position_id = self.record_ref._name == 'carpentry.position' and self.record_ref
            return self.open_position_budget(position_id)
        
        elif self.record_model_id.model in ('account.move.budget.line'):
            # available budget (at project level)
            project = self.record_ref and self.record_ref.project_id
            if project:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'project.project',
                    'view_mode': 'form',
                    'name': project.display_name,
                    'res_id': project.id,
                }
        
        return {}
