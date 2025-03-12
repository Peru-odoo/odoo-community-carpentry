# -*- coding: utf-8 -*-

from odoo import models

class CarpentryGroupAffectation(models.Model):
    _inherit = ['carpentry.group.affectation']

    def _selection_section_res_model(self):
        """ Pickings & Manufacturing Orders are `section_ref` """
        return self._selection_group_res_model() + [
            ('stock.picking', 'Pickings'),
            ('mrp.production', 'Manufacturing Orders')
        ]
    
    
    def _get_budget_section_res_model(self):
        return super()._get_budget_section_res_model() + [
            'stock.picking',
            'mrp.production'
        ]
