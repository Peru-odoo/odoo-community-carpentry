# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command, _

class Launch(models.Model):
    _inherit = "carpentry.group.launch"

    plan_set_id = fields.Many2one(
        'carpentry.plan.set',
        string='Planset',
        domain="[('project_id', '=', project_id)]"
    )
