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

    #===== Fields methods =====#
    def _selection_section_ref(self):
        return [
            (model.model, model.name)
            for model in self.env['ir.model'].sudo().search([])
        ]

    #===== Fields =====#
    state = fields.Selection(
        selection=[('budget', 'Budget'), ('reservation', 'Reservation')],
        string='State',
        readonly=True,
    )
    amount_subtotal = fields.Float(
        string='Remaining',
    )
    section_id = fields.Many2oneReference(
        string='Section ID',
        model_field='section_res_model',
        readonly=True,
    )
    section_ref = fields.Reference(
        string='Name',
        selection='_selection_section_ref',
        readonly=True,
        compute='_compute_section_ref',
    )
    section_model_id = fields.Many2one(
        string='Document Model',
        comodel_name='ir.model',
        readonly=True,
    )
    section_res_model = fields.Char(
        string='Section Model',
        related='section_model_id.model',
    )
    section_model_name = fields.Char(
        string='Document (section)',
        related='section_model_id.name',
    )
    # fields cancelling (necessary so they are not in SQL from ORM)
    phase_id = fields.Many2one(store=False)
    position_id = fields.Many2one(store=False)
    amount_unitary = fields.Float(store=False)
    amount_subtotal_valued = fields.Float(store=False)
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
            self._cr.execute(f"""
                CREATE or REPLACE VIEW %s AS (
                    SELECT
                        row_number() OVER (ORDER BY unique_key) AS id,
                        
                        state,
                        project_id,
                        launch_id,
                        group_model_id,
                        active,

                        section_model_id,
                        section_id,

                        analytic_account_id,
                        amount_subtotal,
                        budget_type
                    FROM (
                        (%s)
                    ) AS result
                )""", (
                    AsIs(self._table),
                    AsIs(') UNION ALL (' . join(queries))
                )
            )

    def _select(self, model, models):
        return f"""
            SELECT
                'available-' || available.id AS unique_key,
                'budget' AS state,
                
                -- project & launch
            	available.project_id,
            	available.launch_id,
                available.group_model_id,
                available.active,

                -- section_model_id: carpentry.position or project.project
                CASE
                    WHEN available.launch_id IS NOT NULL
                    THEN {models['carpentry.position']}
                    ELSE available.group_model_id -- project.project
                END AS section_model_id,
                -- section_id: position or project
                CASE
                    WHEN available.launch_id IS NOT NULL
                    THEN available.position_id
                    ELSE available.project_id
                END AS section_id,

                -- budget
                available.analytic_account_id,
                available.amount_subtotal AS amount_subtotal,
                available.budget_type
            
        """ if model == 'carpentry.budget.available' else f"""

            SELECT
                'reservation-' || reservation.id AS unique_key,
                'reservation' AS state,

                -- project & launch
                reservation.project_id,
                reservation.launch_id,
                CASE
                    WHEN reservation.launch_id IS NOT NULL
                    THEN {models['carpentry.group.launch']}
                    ELSE {models['project.project']}
                END AS group_model_id,
                reservation.active,

                -- section
                reservation.section_model_id,
                reservation.section_id,
                
                -- budget
                reservation.analytic_account_id,
                -1 * reservation.amount_reserved AS amount_subtotal,
                reservation.budget_type

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
        return f"""
            -- no available budget from position, only project and launch
            WHERE available.group_model_id IN (
                {models['project.project']},
                {models['carpentry.group.launch']}
            )
            
            """ if model == 'carpentry.budget.available' else f"""

            WHERE amount_reserved != 0.0
            """
    
    def _groupby(self, model, models):
        return ''
    
    def _orderby(self, model, models):
        return ''

    #===== Compute =====#
    @api.depends('section_id', 'section_model_id')
    def _compute_section_ref(self):
        for remaining in self:
            remaining.section_ref = (
                '{},{}' . format(
                    remaining.section_model_id.model,
                    remaining.section_id,
                )
                if remaining.section_model_id and remaining.section_id
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
    
    def open_section_ref(self, reservation=None):
        if reservation:
            # see `carpentry.budget.reservation`
            self = reservation
        
        """ Opens a document providing or reserving some budget """
        if not self.section_model_id:
            return {}
        
        if self.section_ref and hasattr(self.section_ref, '_carpentry_budget_reservation'):
            # budget reservation
            return {
                'type': 'ir.actions.act_window',
                'name': self.section_ref._description,
                'res_model': self.section_ref._name,
                'res_id': self.section_ref.id,
                'view_mode': 'form',
            }
        
        elif self.section_model_id.model in ('carpentry.position', 'project.project'):
            # available budget
            position_id = self.section_ref._name == 'carpentry.position' and self.section_ref
            return self.open_position_budget(position_id)
        
        elif self.section_model_id.model in ('account.move.budget.line'):
            # available budget (at project level)
            project = self.section_ref and self.section_ref.project_id
            if project:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'project.project',
                    'view_mode': 'form',
                    'name': project.display_name,
                    'res_id': project.id,
                }
        
        return {}
