# -*- coding: utf-8 -*-

from odoo import models, fields

# This adds budget fields & computation to Phases & Launches

class CarpentryGroupLaunch(models.Model):
    _name = 'carpentry.group.launch'
    _inherit = ['carpentry.group.launch', 'carpentry.group.budget.mixin']
