# -*- coding: utf-8 -*-

from odoo import models

class CarpentryGroupAffectation(models.Model):
    _inherit = ['carpentry.group.affectation']

    def _selection_section_res_model(self):
        """ Manufacturing Orders are `section_ref` """
        return self._selection_group_res_model() + [
            ('mrp.production', 'Manufacturing Orders')
        ]
    