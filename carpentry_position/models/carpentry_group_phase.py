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

    def refresh_from_lots(self):
        """ Button to allow refreshing affectations from linked sections.
            This is useful if section's affectations changes **after** the group affectations
        """
        if not self._carpentry_affectation_section:
            return
        
        mapped_model_ids = self._get_mapped_model_ids()
        for group in self:
            # 1. Of current sections, get their positions (for lots) or affectations (for phases)
            #    still affectable (qty_remaining > 0 or not affected) and not already present in the group
            current_record_ids = group.affectation_ids.mapped('record_id')
            section_affectations = (
                group._get_remaining_affectations_from_sections(group._origin.section_ids)
                .filtered(lambda x: x.id not in current_record_ids)
            )

            # 2. Add them to group's affectations
            group._add_affectations_from_sections(section_affectations, mapped_model_ids)


class CarpentryGroupAffectation(models.Model):
    _inherit = ['carpentry.group.affectation']

    def write(self, vals):
        """ When a phase's affectation `quantity_affected` is changed,
            cascade the change to its children (position-to-launch affectation)
        """
        phase_affectations = self.filtered(lambda x: x.group_res_model == 'carpentry.group.phase')
        if phase_affectations and 'quantity_affected' in vals:
            phase_affectations._cascade_affectations(vals['quantity_affected'])
        return super().write(vals)
    
    def _cascade_affectations(self, quantity_affected):
        """ `self` is `phase_affectations`

            If `quantity_affected`...
            a) is 0 -> delete the children affectations
            b) else -> precreate affectation and mirror the `quantity_affected` value
        """
        if not quantity_affected:
            self.affectation_ids.unlink()
        else:
            for group in self.affectation_ids.group_ref:
                group.refresh_from_lots()
            self.affectation_ids.quantity_affected = quantity_affected
