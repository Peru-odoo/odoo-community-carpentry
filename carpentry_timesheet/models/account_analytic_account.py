# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountAnalyticAccount(models.Model):
    _inherit = ['account.analytic.account']

    def _get_timesheetable_types(self):
        return ['service', 'installation'] # , 'production'
