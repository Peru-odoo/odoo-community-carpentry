# -*- coding: utf-8 -*-

from odoo import models

class CarpentryGroupAffectation(models.Model):
    _inherit = ['carpentry.group.affectation']

    def _selection_group_res_model(self):
        """ Tasks are `section_ref` """
        return super()._selection_group_res_model() + [
            ('project.task', 'Tasks')
        ]
    