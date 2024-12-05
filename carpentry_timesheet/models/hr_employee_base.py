# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command

class HrEmployeeBase(models.AbstractModel):
    _inherit = ['hr.employee.base']

    analytic_account_id = fields.Many2one(
        domain=lambda self: self.env['hr.department']._domain_analytic_account_id(),
    )
