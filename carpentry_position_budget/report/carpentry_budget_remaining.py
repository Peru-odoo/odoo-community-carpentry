# -*- coding: utf-8 -*-

from odoo import models, fields, tools, _, api, exceptions
from psycopg2.extensions import AsIs

class CarpentryBudgetRemaining(models.Model):
    """ Union of (+) `carpentry.budget.available` and
                 (-) `carpentry.group.affectation`
    """
    _name = 'carpentry.budget.remaining'
    _inherit = ['carpentry.budget.available']
    _description = 'Remaining budget report'
    _auto = False

    #===== Fields =====#
    state = fields.Selection(
        selection=[('budget', 'Budget'), ('reservation', 'Reservation')],
        string='State',
        readonly=True,
    )
    quantity_affected = fields.Float(
        string='Remaining',
    )
    section_ref = fields.Reference(
        string='Document Name',
        selection=lambda self: self.env['carpentry.group.affectation'].fields_get()['section_ref']['selection'],
        readonly=True,
    )
    section_model_id = fields.Many2one(
        string='Document Model',
        comodel_name='ir.model',
        readonly=True,
    )
    section_model_name = fields.Char(
        string='Document',
        related='section_model_id.name'
    )
    # fields cancelling (necessary so they are not in SQL from ORM)
    position_id = fields.Many2one(store=False)
    phase_id = fields.Many2one(store=False)
    subtotal = fields.Float(store=False)
    amount = fields.Float(store=False)

    #===== View build =====#
    def _get_queries_models(self):
        return ('carpentry.budget.available', 'carpentry.group.affectation')
    
    def _select(self, model):
        models = {x.model: x.id for x in self.env['ir.model'].sudo().search([])}

        return f"""
            SELECT
                available.id AS id_origin,
                'budget' AS state,
                
                -- project & launch
            	available.project_id,
            	available.launch_id,
                available.group_model_id,

                -- section_model_id: carpentry.position or project.project
                CASE
                    WHEN available.launch_id IS NOT NULL
                    THEN (SELECT id FROM ir_model WHERE model = 'carpentry.position')
                    ELSE available.group_model_id -- project.project
                END AS section_model_id,
                -- section_ref: position or project
                CASE
                    WHEN available.launch_id IS NOT NULL
                    THEN 'carpentry.position,' || available.position_id
                    ELSE 'project.project,' || available.project_id
                END AS section_ref,

                -- budget
                available.analytic_account_id,
                available.subtotal AS quantity_affected,
                available.budget_type
            
        """ if model == 'carpentry.budget.available' else f"""

            SELECT
                affectation.id AS id_origin,
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
                ir_model_section.model || ',' || affectation.section_id AS section_ref,
                
                -- budget
                affectation.group_id AS analytic_account_id,
                -1 * affectation.quantity_affected AS quantity_affected,
                affectation.budget_type

        """

    def _from(self, model):
        return (
            'FROM carpentry_budget_available AS available'

            if model == 'carpentry.budget.available' else
	        
            'FROM carpentry_group_affectation AS affectation'
        )

    def _join(self, model):
        return """
            INNER JOIN ir_model AS ir_model_group
                ON ir_model_group.id = available.group_model_id
            
        """ if model == 'carpentry.budget.available' else f"""

            INNER JOIN ir_model AS ir_model_section
                ON ir_model_section.id = affectation.section_model_id
        """
    
    def _where(self, model):
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
    
    def _groupby(self, model):
        return ''
    
    def _orderby(self, model):
        return ''
    
    #===== Buttons =====#
    def open_section_ref(self):
        """ Opens a document providing or reserving some budget """
        if not self.section_model_name:
            return
        
        if self.section_model_id.model in ('carpentry.position', 'project.project'):
            # available budget
            position_id = self.section_ref._name == 'carpentry.position' and self.section_ref
            return self.open_position_budget(position_id)
        else:
            # budget reservation
            return {
                'type': 'ir.actions.act_window',
                'name': self.section_ref._description,
                'res_model': self.section_ref._name,
                'res_id': self.section_ref.id,
                'view_mode': 'form',
            }
