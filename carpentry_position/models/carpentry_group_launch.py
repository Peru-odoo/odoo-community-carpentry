# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.osv import expression

class Launch(models.Model):
    _name = "carpentry.group.launch"
    _description = "Launch"
    _inherit = ['carpentry.group.mixin', 'carpentry.group.affectation.mixin']
    _carpentry_affectation_allow_m2m = False
    _carpentry_affectation_section = 'phase'
    
    #===== Fields (from `affectation.mixin`) =====#
    affectation_ids = fields.One2many(
        domain=lambda self: f"[('group_res_model', '=', '{self._name}'), ('project_id', '=', project_id)]",
    )
    section_ids = fields.One2many(
        comodel_name='carpentry.group.phase',
    )

    #===== Compute: Temp<->Real affectation logics =====#
    @api.depends('affectation_ids')
    def _compute_affectation_ids_temp(self):
        for launch in self:
            matrix = launch._get_affectation_ids_temp()
            launch.affectation_ids_temp = matrix
    
    #====== Affectation matrix ======#
    def _get_affect_vals(self, mapped_model_ids, record_ref, group_ref, affectation=False):
        return super()._get_affect_vals(mapped_model_ids, record_ref, group_ref, affectation) | {
            'affected': False,
        }
    
    def _get_record_refs(self):
        """ Lines of Launches affectation matrix are either:
            - all project's Phases' affectations in x2many_2d_matrix
            - linked phases' affectation in launch form
        """
        if self._context.get('x2many_2d_matrix'):
            phase_ids = self.project_id.phase_ids
        else:
            phase_ids = self.section_ids
        
        return phase_ids.affectation_ids.filtered(
            lambda x: x.quantity_affected > 0
        )
    
    def _get_unlink_domain(self):
        """ Launch are:
            - group: for standard affectations
            - record: for budget
            This prevents removing budget reservation when deleting launch
        """
        return self._get_domain_affect('group')
    
    def _default_quantity(self, record_ref, group_ref):
        """ Copy `quantity_affected` of phase affectation
            (for `_compute_sum_quantity_affected`)
        """
        return record_ref.quantity_affected

    def affect_all(self):
        affectations = self.affectation_ids.filtered('is_affectable')
        affectations.affected = True
    