# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class AnalyticAccount(models.Model):
    _inherit = ['account.analytic.account']
    _carpentry_affectation_quantity = True # to allow affectation by qty
