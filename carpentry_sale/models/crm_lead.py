# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Lead(models.Model):
    _inherit = 'crm.lead'

    def _get_copied_vals(self):
        return super()._get_copied_vals() | {
            'market': self.expected_revenue
        }
