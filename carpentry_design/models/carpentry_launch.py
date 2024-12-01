# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command, _

class Launch(models.Model):
    _inherit = ["carpentry.group.launch"]

    plan_set_id = fields.Many2one(
        comodel_name='carpentry.plan.set',
        string='Plan set',
        domain="[('project_id', '=', project_id)]"
    )
