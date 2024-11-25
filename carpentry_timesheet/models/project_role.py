# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProjectRole(models.Model):
    _inherit = "project.role"

    product_id = fields.Many2one(related='department_id.product_id')
