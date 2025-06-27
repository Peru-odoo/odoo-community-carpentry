# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryGroupLaunch(models.Model):
    _inherit = ['carpentry.group.launch']

    task_ids = fields.Many2many(
        # reverse many2many, used in PO
        string='Tasks',
        comodel_name='project.task',
        relation='carpentry_group_launch_project_task_rel',
        column1='launch_id',
        column2='task_id',
    )
