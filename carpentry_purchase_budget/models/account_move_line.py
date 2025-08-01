# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = ['account.move.line']

    #==== project_id cascade & from analytic distribution ====#
    project_id = fields.Many2one(related='')

    def _get_fields_project_id(self):
        return ['move_id']
    
    def _should_enforce_internal_analytic(self):
        """ Forces analytic of *internal* project for all *storable* lines """
        return self.product_id.type == 'product'
    
    def _compute_analytic_distribution(self):
        res = super()._compute_analytic_distribution()
        self._compute_analytic_distribution_carpentry()
        return res
    