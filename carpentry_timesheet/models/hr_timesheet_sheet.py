# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _default_product_id(self):
        return self.env.user.employee_id.product_id.last_variant_id.id
    
    product_id = fields.Many2one(readonly=False, store=True, default=_default_product_id, compute='_compute_product_id')
    hide_product_id = fields.Boolean(store=False, default=lambda self: not self.env.user.has_group('project.group_project_manager'))

    #===== Compute =====#
    @api.depends('task_id')
    def _compute_product_id(self):
        """ Set `task_id.product_id` as aal's `product_id` without erasing existing value """
        for aal in self:
            if aal.task_id.id and not aal.product_id.id:
                aal.product_id = aal.task_id.product_id.last_variant_id.id

class Sheet(models.Model):
    _inherit = 'hr_timesheet.sheet'

    def _default_add_line_product_id(self):
        return self.env.user.employee_id.product_id.last_variant_id.id
    
    add_line_product_id = fields.Many2one('product.product', string="Product", domain=[('is_timesheetable', '=', True)],
        default=_default_add_line_product_id)
    hide_product_id = fields.Boolean(compute='_compute_hide_product_id')

    #===== Constrains =====#
    @api.onchange('add_line_project_id', 'add_line_product_id')
    def _onchange_task_consistency(self):
        """ Ensure Task is consistent with Project and Budget fields, else reset it """
        for timesheet in self:
            if self.add_line_task_id.id not in self.add_line_project_id.task_ids.ids or \
             self.add_line_product_id.id not in self.add_line_task_id.product_id.product_variant_ids.ids:
                timesheet.add_line_task_id = False

    #===== Compute =====#
    def _compute_hide_product_id(self):
        """ Only Project Manager may log timesheets on tasks other than their default product """
        for sheet in self:
            sheet.hide_product_id = not self.env.user.has_group('project.group_project_manager')

    #===== Business methods =====#
    def add_line(self):
        """ Make Task required """
        self._onchange_task_consistency()
        if not self.add_line_project_id.id or not self.add_line_task_id.id:
            raise exceptions.UserError(_('Please select both Project and Task to add a line.'))
        return super().add_line()
    def reset_add_line(self):
        self.write({"add_line_project_id": False, "add_line_task_id": False, "add_line_product_id": self._default_add_line_product_id()})
    
    def action_timesheet_copy_previous(self):
        """ Import into current sheet all lines of immediate previous sheet (with empty timesheet values) """
        previous_id = self.env['hr_timesheet.sheet'].search([('user_id', '=', self.env.uid), ('id', '!=', self.id)], limit=1)
        if not previous_id.id:
            raise exceptions.UserError(_('No previous timesheet to copy.'))
        else:
            for aal in previous_id.timesheet_ids:
                self._fake_fill_add_line(aal.project_id, aal.task_id) 
                self.add_line()
                self._fake_fill_add_line() 
    def _fake_fill_add_line(self, project_id=False, task_id=False):
        self.add_line_project_id = project_id
        self.add_line_task_id = task_id
    def delete_empty_lines(self, delete_empty_rows=False):
        """ Avoid removing empty lines when adding new ones """
        return
