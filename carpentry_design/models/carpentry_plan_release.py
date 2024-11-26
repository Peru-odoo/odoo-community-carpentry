# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from odoo.addons.carpentry_planning.models.carpentry_planning_card import PLANNING_CARD_COLOR

import calendar

class PlanRelease(models.Model):
    _name = "carpentry.plan.release"
    _description = "Plan Release"
    _inherit = ["carpentry.planning.mixin"]
    _order = "date_plan_release"
    _date_name = "date_plan_release"

    #===== Fields' methods =====#
    @api.model
    def _group_expand_plan_set_id(self, records, domain, order):
        """ In Tree view groupped by Plansets, also render the Plansets with no Planset Releases """
        new_domain = [('release_ids','=',False)]
        if 'default_project_id' in self._context:
            new_domain += [('project_id', '=', self._context['default_project_id'])]
        elif records.project_id.ids:
            new_domain += [('project_id', 'in', records.project_id.ids)]
        return (records | records.search(new_domain, order=order)).sorted()

    #===== Fields =====#
    # relational
    project_id = fields.Many2one(
        related='plan_set_id.project_id',
        store=True
    )
    plan_set_id = fields.Many2one(
        comodel_name='carpentry.plan',
        string='Planset',
        required=True,
        index='btree_not_null',
        group_expand='_group_expand_plan_set_id',
        ondelete='cascade'
    )
    launch_ids = fields.One2many(
        related='plan_set_id.launch_ids'
    )

    # main fields
    name = fields.Char(
        string='Index',
        required=True
    )
    description = fields.Text(
        string='Comment'
    )
    plan_set_name = fields.Char(
        related='plan_set_id.name'
    )
    date_plan_release = fields.Date(
        string='Date Plan release',
        default=fields.Date.today(),
        required=True
    )
    date_visa_feedback = fields.Date(
        string='Date Visa feedback'
    )
    # computed
    week_plan_release = fields.Integer(
        compute='_compute_weeks'
    )
    week_visa_feedback = fields.Integer(
        compute='_compute_weeks'
    )

    # state & active
    state = fields.Selection(
        selection=[
            ('muted', 'Stand-by'),
            ('success', 'Accepted'),
            ('warning', 'Defect'),
            ('danger', 'Refused')
        ],
        default='muted',
        required=True
    )
    state_color = fields.Integer(
        compute='_compute_state_color'
    )
    active = fields.Boolean(
        string='Active?',
        default=True
    )

    # planning
    sequence = fields.Integer(
        # mandatory for planning: computed based on date_plan_release
        compute='_compute_sequence',
        store=True
    )
    planning_card_color_is_auto = fields.Boolean(
        default=True, store=False
    )
    planning_card_color = fields.Integer(
        compute='_compute_state_color'
    )
    planning_card_body_color = fields.Selection(
        string='Planning Card Body Color',
        related='state'
    )

    #===== Compute =====#
    @api.depends('date_plan_release', 'date_visa_feedback')
    def _compute_weeks(self):
        for release in self:
            release.week_plan_release = release.date_plan_release.isocalendar()[1]
            release.week_visa_feedback = bool(release.date_visa_feedback) and release.date_visa_feedback.isocalendar()[1]
    
    #===== Planning =====#
    @api.depends('state')
    def _compute_state_color(self):
        for release in self:
            release.state_color = PLANNING_CARD_COLOR[release.state]
            release.planning_card_color = release.state_color
    
    @api.depends('date_plan_release')
    def _compute_sequence(self):
        for release in self:
            release.sequence = calendar.timegm(release.date_plan_release.timetuple())

    @api.model
    def _get_planning_subheaders(self, column_id, launch_id):
        return {
            'description': launch_id.plan_set_id.name,
            # 'budgets': [] # todo
        }
