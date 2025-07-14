# -*- coding: utf-8 -*-

from odoo import models, fields, tools, _, api, exceptions
from psycopg2.extensions import AsIs

class CarpentryBudgetRemaining(models.Model):
    """ Union of (+) `carpentry.budget.available` and
                 (-) `carpentry.group.affectation`
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
    quantity_affected = fields.Float(
        string='Remaining',
        help='',
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
        string='Document',
        related='section_model_id.name',
    )
    # fields cancelling (necessary so they are not in SQL from ORM)
    position_id = fields.Many2one(store=False)
    phase_id = fields.Many2one(store=False)
    subtotal = fields.Float(store=False)
    amount = fields.Float(store=False)

    #===== View build =====#
    def _get_queries_models(self):
        return ('carpentry.budget.available', 'carpentry.group.affectation')
    
    def _select(self, model, models):
        return f"""
            SELECT
                'available-' || available.id AS unique_key,
                'budget' AS state,
                
                -- project & launch
            	available.project_id,
            	available.launch_id,
                available.group_model_id,

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
                available.subtotal AS quantity_affected,
                available.budget_type
            
        """ if model == 'carpentry.budget.available' else f"""

            SELECT
                'reservation-' || affectation.id AS unique_key,
                'reservation' AS state,

                -- project & launch
                affectation.project_id,
                CASE
                    WHEN affectation.record_model_id = {models['carpentry.group.launch']}
                    THEN affectation.record_id
                    ELSE NULL
                END AS launch_id,
                affectation.record_model_id AS group_model_id,

                -- section
                ir_model_section.id AS section_model_id,
                affectation.section_id AS section_id,
                
                -- budget
                affectation.group_id AS analytic_account_id,
                -1 * affectation.quantity_affected AS quantity_affected,
                affectation.budget_type

        """

    def _from(self, model, models):
        return (
            'FROM carpentry_budget_available AS available'

            if model == 'carpentry.budget.available' else
	        
            'FROM carpentry_group_affectation AS affectation'
        )

    def _join(self, model, models):
        return """
            INNER JOIN ir_model AS ir_model_group
                ON ir_model_group.id = available.group_model_id
            
        """ if model == 'carpentry.budget.available' else f"""

            INNER JOIN ir_model AS ir_model_section
                ON ir_model_section.id = affectation.section_model_id
        """
    
    def _where(self, model, models):
        return """
            WHERE
                (project_id IS NOT NULL OR
                launch_id IS NOT NULL) AND
                ir_model_group.model != 'carpentry.group.phase' -- no available budget from phase
            
            """ if model == 'carpentry.budget.available' else f"""

            WHERE
                affectation.active IS TRUE AND
                quantity_affected != 0 AND
                budget_type IS NOT NULL
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

    #===== Buttons =====#
    def open_section_ref(self, affectation=None):
        if affectation:
            # see `carpentry.group.affectation`
            self = affectation
        
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
