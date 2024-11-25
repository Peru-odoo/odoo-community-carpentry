# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command

class HrDepartment(models.Model):
    _inherit = 'hr.department'

    product_id = fields.Many2one('product.template', string='Default Product on task', domain=[('is_timesheetable', '=', True)])
