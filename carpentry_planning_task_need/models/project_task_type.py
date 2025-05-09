# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class TaskType(models.Model):
    _inherit = ['project.task.type']

    need_default = fields.Boolean(
        string='Default for Needs',
        default=False,
        help='Default stage for Needs creation before their activation '
             'from the planning page.',
    )
