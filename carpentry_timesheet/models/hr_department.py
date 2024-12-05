# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command

class HrDepartment(models.Model):
    _inherit = ['hr.department']

    analytic_account_id = fields.Many2one(
        # Lock possible HR analytic account to the ones with cost information
        domain="""[
            ('timesheetable', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', company_id),
        ]"""
    )
