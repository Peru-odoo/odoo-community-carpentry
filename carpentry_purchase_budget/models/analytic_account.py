# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class AnalyticAccount(models.Model):
    _inherit = ['account.analytic.account']
    _carpentry_affectation = True # to allow affectation (as `group_ref`)
    _carpentry_affectation_quantity = True # affectation by qty
    _carpentry_affectation_allow_m2m = True
    _carpentry_affectation_section = False
