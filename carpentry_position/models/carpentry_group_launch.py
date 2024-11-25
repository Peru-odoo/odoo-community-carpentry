# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from collections import defaultdict

class Launch(models.Model):
    _name = "carpentry.group.launch"
    _description = "Launch"
    _inherit = ['carpentry.group.mixin', 'carpentry.group.affectation.mixin']
    _carpentry_affectation_allow_m2m = False
    _carpentry_affectation_section = 'phase'
    
    #===== Fields (from `affectation.mixin`) =====#
    affectation_ids = fields.One2many(
        domain=[('group_res_model', '=', _name)]
    )
    section_ids = fields.One2many(
        comodel_name='carpentry.group.phase',
    )

    #====== Affectation matrix ======#
    def _get_compute_record_refs(self):
        """ Lines of Launches affectation matrix are Phases' affectations """
        return self.project_id.phase_ids.affectation_ids
    