# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class ProjectRole(models.Model):
    _inherit = ["project.role"]

    assignment_ids = fields.One2many(
        # needed for `_get_default_type_id()` and on `carpentry.need.family`
        comodel_name="project.assignment",
        inverse_name="role_id",
        string="Project Assignments"
    )
