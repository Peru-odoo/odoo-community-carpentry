# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command

class HrEmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    product_id = fields.Many2one(related='department_id.product_id')
