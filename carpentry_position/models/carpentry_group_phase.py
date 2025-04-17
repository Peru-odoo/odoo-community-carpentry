# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class CarpentryGroupPhase(models.Model):
    _name = "carpentry.group.phase"
    _description = "Phase"
    _inherit = ['carpentry.group.mixin', 'carpentry.group.affectation.mixin']
    _carpentry_affectation_quantity = True
    _carpentry_affectation_section = 'lot'
    _carpentry_affectation_section_of = 'launch'
    
    #===== Fields (from `affectation.mixin`) =====#
    affectation_ids = fields.One2many(
        domain=[('group_res_model', '=', _name)]
    )
    section_ids = fields.One2many(
        comodel_name='carpentry.group.lot',
    )

    #====== Affectation matrix ======#
    def _get_record_refs(self):
        """ Lines of Phases affectation matrix are Project' Positions """
        return self.project_id.position_ids

    @api.model
    def _get_quantities_available(self, affectations):
        """ `Available quantity` in phase affectation is position's quantity in the project """
        return {
            (x.record_res_model, x.record_id, x.group_id): x.record_ref.quantity
            for x in affectations
        }


class CarpentryGroupAffectation(models.Model):
    _inherit = ['carpentry.group.affectation']

    def write(self, vals):
        """ When a phase's affectation `quantity_affected` is changed to 0,
            *cascade-delete* the child(ren) launch-to-position affectations
        """
        phase_affectations = self.filtered(lambda x: x.group_res_model == 'carpentry.group.phase')
        if (
            phase_affectations and
            'quantity_affected' in vals and
            vals['quantity_affected'] == 0.0
        ):
            self.affectation_ids.unlink()
        return super().write(vals)
