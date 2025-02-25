# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command, SUPERUSER_ID
from odoo.osv.expression import AND

class HrTimesheetSheet(models.Model):
    _inherit = ['hr_timesheet.sheet']

    #===== Fields =====#
    add_line_project_id = fields.Many2one(
        default=lambda self: self.env['project.default.mixin']._get_project_id(),
    )
    is_internal_project = fields.Boolean(
        related='add_line_project_id.is_internal_project'
    )
    add_line_analytic_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Budget',
        default=lambda self: self.env.user.employee_id and self.env.user.employee_id._get_analytic_account_id(),
        domain="[('timesheetable', '=', True), ('budget_project_ids', '=', add_line_project_id)]"
    )
    
    #===== Compute / onchange =====#
    @api.onchange('add_line_project_id', 'add_line_task_id')
    def _onchange_task_consistency(self):
        """ [UI] Clean `add_line_task_id` if `add_line_project_id` is changed
            after a `add_line_task_id` was selected by user.

            This finishes to enforce timesheeted tasks belong to their project
        """
        for sheet in self:
            if sheet.add_line_task_id.id and sheet.add_line_task_id.id not in sheet.available_task_ids.ids:
                sheet.add_line_task_id = False
    
    @api.depends('add_line_analytic_id')
    def _compute_available_task_ids(self):
        """ Restrict selectable tasks to:
            1. timesheetable
            2. filter by analytic (budget)
            3. *and*, if user is not a timesheet approver:
                - project visible by all users, *or*
                - on which user is assigned, *or*
                - tasks of Internal project and not used in *HR Leaves* 
            4. *and* tasks not configured on Leaves
               (compatibility with bridge module `project_timesheet_holidays`)
        """
        res = super()._compute_available_task_ids()

        # 1.
        domain = [('allow_timesheets', '=', True)]

        # 2.
        if self.add_line_analytic_id and not self.is_internal_project:
            domain += [('analytic_account_id', 'in', self.add_line_analytic_id.ids)]
        
        # 3.
        if not self.env.user.has_group('hr_timesheet.group_hr_timesheet_approver'):
            domain += ['|', '|',
                ('project_id.privacy_visibility', 'in', ['employees', 'portal']),
                ('user_ids', '=', self.env.uid),
                ('project_id.is_internal_project', '=', True),
            ]

        # 4.
        if hasattr(self.available_task_ids, 'is_timeoff_task'):
            domain = AND([domain, [('is_timeoff_task', '=', False)]])
        print('domain', domain)
        
        self.available_task_ids = self.available_task_ids.filtered_domain(domain)
        
        return res

    #===== Business methods =====#
    def add_line(self):
        """ Make `add_line_task_id` required """
        self._onchange_task_consistency()

        if not self.add_line_project_id.id or not self.add_line_task_id.id:
            raise exceptions.UserError(_(
                'Please select both Project and Task to add a line.'
            ))
        
        return super().add_line()
    