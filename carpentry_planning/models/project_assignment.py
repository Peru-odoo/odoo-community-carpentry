# -*- coding: utf-8 -*-

from odoo import models, fields

class ProjectAssignment(models.Model):
    _inherit = ["project.assignment"]

    config_planning_next_project = fields.Boolean(
        related='role_id.config_planning_next_project',
    )
    project_fold = fields.Boolean(
        related='project_id.stage_id.fold',
    )
