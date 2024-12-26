# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class CarpentryGroupPhase(models.Model):
    _name = "carpentry.group.phase"
    _description = "Phase"
    _inherit = ['carpentry.group.mixin', 'carpentry.group.affectation.mixin']
    _carpentry_affectation_quantity = True
    _carpentry_affectation_section = 'lot'
    
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
