# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    employee_ids = fields.One2many('hr.employee', 'product_id', string='Employees')
    is_timesheetable = fields.Boolean(string='Is timesheetable?', compute='_compute_is_timesheetable', search='_search_is_timesheetable')

    def _compute_is_timesheetable(self):
        for product in self:
            product.is_timesheetable = product.detailed_type in ['service_office']
    @api.model
    def _search_is_timesheetable(self, operator, value):
        return [('detailed_type', 'in', ['service_office'])]
