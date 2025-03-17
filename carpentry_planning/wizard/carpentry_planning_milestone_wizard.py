# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

import datetime

class PlanningMilestoneWizard(models.Model):
    _name = "carpentry.planning.milestone.wizard"
    _description = "Planning Milestone Wizard"

    #===== Fields' methods =====#
    def default_get(self, fields):
        """ Whether the wizard should trigger other milestones shift
            => it depends on the shifted milestone
        """
        vals = super().default_get(fields)

        milestone_id_ = fields.get('milestone_id') or self._context.get('milestone_id')
        milestone_id = self.env['carpentry.planning.milestone'].browse(milestone_id_)
        if 'shift' in fields and milestone_id:
            vals['shift'] = milestone_id._should_shift()

        return vals

    #===== Fields =====#
    milestone_id = fields.Many2one(
        comodel_name='carpentry.planning.milestone',
        string='Milestone',
        required=True
    )
    launch_id = fields.Many2one(
        related='milestone_id.launch_id'
    )
    date_origin = fields.Date(
        related='milestone_id.date',
        string='Current date'
    )
    date_new = fields.Date(
        string='New date'
    )
    offset = fields.Integer(
        string='Offset in week(s)'
    )
    shift = fields.Boolean(
        string='Shift',
        help='If activated, the other start and end date of the launch will be'
             ' updated of the same offset.'
    )

    #===== Onchange =====#
    @api.onchange('date_new')
    def _compute_date_new(self):
        for wizard in self:
            d1, d2 = wizard.date_origin, wizard.date_new
            if not d1 or not d2:
                continue
            
            monday1 = (d1 - datetime.timedelta(days=d1.weekday()))
            monday2 = (d2 - datetime.timedelta(days=d2.weekday()))

            wizard.offset = (monday2 - monday1).days / 7
    
    @api.onchange('offset')
    def _onchange_offset(self):
        for wizard in self:
            if not wizard.date_origin:
                continue
                
            wizard.date_new = wizard.date_origin + datetime.timedelta(days = 7 * wizard.offset)

    #===== Action =====#
    def button_set_date(self):
        """ Shift siblings date of the same offset that the update. Example:
             +1 week of production start => make +1 week of all other `start` and
             `end` dates of the same launch
            
            If changed date is `shift=False`, nothing happen
            If changed date is `shift=True`, changes are synched only with dates
             also having `shift=True`
        """
        for wizard in self:
            # calculate `should_shift` before setting date
            should_shift = wizard.shift and wizard.date_origin and wizard.date_new

            # set date
            wizard.milestone_id.date = wizard.date_new

            # shift siblings
            if should_shift:
                siblings = wizard.launch_id.milestone_ids - wizard.milestone_id
                to_shift = siblings.filtered(lambda x: x.date and x._should_shift())
                for sibling in to_shift:
                    sibling.date += datetime.timedelta(days = 7 * wizard.offset)
        
        return self
