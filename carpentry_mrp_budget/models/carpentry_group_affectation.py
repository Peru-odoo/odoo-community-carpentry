# -*- coding: utf-8 -*-

from odoo import models

class CarpentryGroupAffectation(models.Model):
    _inherit = ['carpentry.group.affectation']

    def _selection_section_res_model(self):
        """ Pickings & Manufacturing Orders are `section_ref` """
        return super()._selection_section_res_model() + [
            ('stock.picking', 'Pickings'),
            ('mrp.production', 'Manufacturing Orders')
        ]
