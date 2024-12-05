# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command

class HrEmployeeBase(models.AbstractModel):
    _inherit = ['hr.employee.base']

    analytic_account_id = fields.Many2one(
        domain="""[
            ('timesheetable', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', company_id),
        ]""",
    )
