# -*- coding: utf-8 -*-

from odoo import models, fields

# This adds budget fields & computation to Phases & Launches

class CarpentryGroupPhase(models.Model):
    _name = 'carpentry.group.phase'
    _inherit = ['carpentry.group.phase', 'carpentry.group.budget.mixin']

