# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command, _

class PlanSet(models.Model):
    _name = "carpentry.plan.set"
    _description = "Plan Set"
    _inherit = [
        'carpentry.group.mixin',
        'mail.thread', 'mail.activity.mixin'
    ]

    launch_ids = fields.One2many(
        comodel_name='carpentry.group.launch',
        inverse_name='plan_set_id',
        string='Launches',
        domain="[('project_id', '=', project_id), '|', ('plan_set_id', '=', False), ('plan_set_id', '=', id)]"
    )
    plan_release_ids = fields.One2many(
        comodel_name='carpentry.plan.release',
        inverse_name='plan_set_id',
        string='Releases'
    )

    # -- UI fields --
    last_release_id = fields.Many2one(
        comodel_name='carpentry.plan.release',
        compute='_compute_last_release_id',
        string='Last Release',
        store=True # save for perf optim.
    )
    last_release_description = fields.Text(
        string='Last Comment',
        related='last_release_id.description'
    )
    last_release_week_publish = fields.Integer(
        string='Last Publishing',
        related='last_release_id.week_publish'
    )
    last_release_week_visa_feedback = fields.Integer(
        string='Last Visa',
        related='last_release_id.week_visa_feedback'
    )
    last_release_state = fields.Selection(
        string='Last State',
        related='last_release_id.state',
        store=True # for groupby
    )

    #===== Compute =====#
    @api.depends('plan_release_ids', 'plan_release_ids.date_plan_publish')
    def _compute_last_release_id(self):
        """ Save last plan release, which is the 1st following 
            ORDER BY clause of `carpentry.plan.release`
        """
        for plan in self:
            plan.last_release_id = fields.first(plan.plan_release_ids)

    #===== Button =====#
    def action_open_planning_task_tree(self):
        return self.env['project.task'].action_open_planning_tree(record_id=self)
