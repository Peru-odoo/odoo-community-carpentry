# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class ProductTemplate(models.Model):
    _inherit = ['product.template']

    product_substitution_id = fields.Char(
        string='Substitution Product',
        help='Product that will serve as component in Work Order'
             ' in replacement of this one.'
    )
