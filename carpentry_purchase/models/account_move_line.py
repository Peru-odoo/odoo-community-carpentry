# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command, _

class AccountMoveLine(models.Model):
    _inherit = ['account.move.line']

    project_id = fields.Many2one(
        related='move_id.project_id'
    )
