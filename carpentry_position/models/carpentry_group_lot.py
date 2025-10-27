# -*- coding: utf-8 -*-

from odoo import api, models, fields

class Lot(models.Model):
    _name = "carpentry.group.lot"
    _inherit = ['carpentry.group.phase', 'carpentry.affectation.mixin']
    _description = "Lots"
    _carpentry_field_affectations = 'position_ids'
    
    #===== Fields =====#
    # from mixins
    affectation_ids = fields.One2many(inverse_name='lot_id',)
    position_ids = fields.One2many(inverse_name='lot_id', compute='',)
    