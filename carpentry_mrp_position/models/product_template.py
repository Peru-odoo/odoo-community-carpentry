# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class ProductTemplate(models.Model):
    _inherit = ['product.template']

    production_ok = fields.Boolean(
        string='Can be manufactured',
        default=False
    )
    