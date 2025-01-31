# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command, _

class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'project.default.mixin']

    project_id = fields.Many2one(
        required=False,
    )
