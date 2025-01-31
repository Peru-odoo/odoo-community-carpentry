# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = ['res.company']

    # compatibility with `hr_timesheet`
    internal_project_id = fields.Many2one(
        comodel_name='project.project', string='Internal Project'
    )
