# -*- coding: utf-8 -*-

from odoo import models, fields

class Lot(models.Model):
    _name = "carpentry.group.lot"
    _description = "Lots"
    _inherit = ['carpentry.group.mixin', 'carpentry.group.affectation.mixin']
    _order = 'sequence, id'
    
    #===== Fields (from `affectation.mixin`) =====#
    # `affectation_ids` should be named `position_ids`, but it's a cheat for `_inverse_section_ids`
    affectation_ids = fields.One2many(
        comodel_name='carpentry.position',
        inverse_name='lot_id',
        string='Positions',
        domain=[]
    )
    sum_position_quantity_affected = fields.Integer(
        # cancel this field from mixin, which is not needed for lots
        compute=False,
        store=False
    )
