# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class ProjectType(models.Model):
    _inherit = ['project.type']

    analytic_account_id = fields.Many2one(
        domain=[('timesheetable', '=', True)],
    )
