# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions, _, Command

class ProjectRole(models.Model):
    _inherit = ["project.role"]
    _order = "sequence, name"

    sequence = fields.Integer()
    fold = fields.Boolean(
        default=False,
        help='If activated, will be folded by default on Assignation kanban view.'
    )
