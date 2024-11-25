# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command, _

class PlanSet(models.Model):
    _name = "carpentry.plan.set"
    _description = "Plan Set"
    _inherit = ["carpentry.group.mixin"]
    _rec_name = 'display_name'

    sequence = fields.Integer(
        readonly=False
    )
    launch_ids = fields.One2many(
        'carpentry.launch',
        'plan_set_id',
        string='Launches',
        domain="[('project_id', '=', project_id), '|', ('plan_set_id', '=', False), ('plan_set_id', '=', id)]"
    )
    release_ids = fields.One2many(
        'carpentry.plan.release',
        'plan_set_id',
        string='Releases'
    )
    
    #===== Compute =====#
    def _compute_display_name(self):
        for plan in self:
            plan.display_name = f'{plan.project_id.display_name} - {plan.name}'
