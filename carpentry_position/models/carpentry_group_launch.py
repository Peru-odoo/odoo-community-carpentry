# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Launch(models.Model):
    _name = "carpentry.group.launch"
    _inherit = ['carpentry.group.phase', 'carpentry.affectation.mixin']
    _description = "Launch"
    _carpentry_field_parent_group = 'phase_id'
    _carpentry_field_record = 'parent_id' # phase_affectation
    
    #===== Fields (from `affectation.mixin`) =====#
    affectation_ids = fields.One2many(
        inverse_name='launch_id',
        domain=[('mode', '=', 'launch')],
    )
    phase_ids = fields.One2many(
        inverse='_inverse_parent_group_ids',
    )

    def button_affect_all_positions(self):
        self.affectation_ids.filtered('is_affectable').affected = True
    