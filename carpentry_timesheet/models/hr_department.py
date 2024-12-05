# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command

class HrDepartment(models.Model):
    _inherit = ['hr.department']

    def _domain_analytic_account_id(self):
        """ Lock possible HR analytic account to the ones with cost information """
        return """[
            ('timesheetable', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', company_id),
        ]"""

    analytic_account_id = fields.Many2one(
        domain=_domain_analytic_account_id
    )
