# -*- coding: utf-8 -*-

from odoo import models

class CarpentryGroupAffectation(models.Model):
    _inherit = ['carpentry.group.affectation']

    def _selection_section_res_model(self):
        """ Purchase Order are `section_ref` """
        return self._selection_group_res_model() + [
            ('purchase.order', 'Purchase Order')
        ]
    
    def _get_budget_section_res_model(self):
        return self._get_budget_section_res_model() + ['purchase.order']
