# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class Project(models.Model):
    _name = "project.project"
    _inherit = ["project.project", "carpentry.affectation.mixin"]

    #===== Fields =====#
    affectation_ids = fields.One2many(inverse_name='project_id',)
    position_ids =    fields.One2many(inverse_name='project_id', compute='',)
    lot_ids =         fields.One2many(inverse_name='project_id', compute='',)
    phase_ids =       fields.One2many(inverse_name='project_id', compute='',)
    launch_ids =      fields.One2many(inverse_name='project_id', compute='',)
    position_count =  fields.Integer(store=True,)
    position_fully_affected = fields.Boolean(compute='_compute_affectation_status')
    #-- cancel fields from mixin --
    quantity_remaining_to_affect = fields.Integer(compute='',store=False,)
    
    # cancel from mixin
    _sql_constraints = [('name_per_project', 'check(1=1)', ''),]

    #===== Compute =====
    @api.depends('position_ids.state')
    def _compute_affectation_status(self):
        """ Position's affectation status at project-scope """
        for project in self:
            project.position_fully_affected = (
                not project.position_ids
                or set(project.position_ids.mapped('state')) == {'done'}
            )
    def _get_warning_banner(self):
        """ Inherited in `carpentry.position.budget` """
        return not self.position_fully_affected
