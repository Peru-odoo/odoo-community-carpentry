# -*- coding: utf-8 -*-

from odoo import models, fields

class ProjectRole(models.Model):
    _inherit = ["project.role"]

    config_planning_next_project = fields.Boolean(
        string='Planning next project',
        help="Whether this role is used to generate the 'Next projects' list "
             "on the planning.",
        default=False,
    )
