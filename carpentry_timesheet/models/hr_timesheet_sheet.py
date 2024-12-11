# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command, SUPERUSER_ID

class HrTimesheetSheet(models.Model):
    _inherit = ['hr_timesheet.sheet']

    #===== Fields methods =====#
    @api.model
    def _group_expand_add_line_project_id(self, projects, domain, order):
        """ View all role in assignation kanban view """
        project_ids_ = projects._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return projects.browse(project_ids_)

    #===== Fields =====#
    add_line_project_id = fields.Many2one(
        group_expand='_group_expand_add_line_project_id'
    )

    #===== Project/Task consistency (UI) =====#
    @api.onchange('add_line_project_id', 'add_line_task_id')
    def _onchange_task_consistency(self):
        """ Clean `add_line_task_id` if `add_line_project_id` is changed
            after a `add_line_task_id` was selected by user.

            This finishes to enforce timesheeted tasks belong to their project
        """
        for sheet in self:
            if sheet.add_line_task_id.id and sheet.add_line_task_id.id not in sheet.available_task_ids.ids:
                sheet.add_line_task_id = False

    #===== Business methods =====#
    def add_line(self):
        """ Make `add_line_task_id` required """
        self._onchange_task_consistency()

        if not self.add_line_project_id.id or not self.add_line_task_id.id:
            raise exceptions.UserError(_(
                'Please select both Project and Task to add a line.'
            ))
        
        return super().add_line()
    