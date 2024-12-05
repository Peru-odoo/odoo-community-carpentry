# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class HrTimesheetSheet(models.Model):
    _inherit = ['hr_timesheet.sheet']

    # add_line_project_id = fields.Many2one(
    #     domain=lambda self: [
    #         ('favorite_user_ids', '=', self.env.uid),
    #         ('stage_id.fold', '=', False)
    #     ]
    # )

    #===== Project/Task consistency (UI) =====#
    @api.onchange('add_line_project_id', 'add_line_product_id')
    def _onchange_task_consistency(self):
        """ Clean `add_line_task_id` if `add_line_project_id` is changed
            after a `add_line_task_id` was selected by user.

            This finishes to enforce timesheeted tasks belong to their project
        """
        for timesheet in self:
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
    