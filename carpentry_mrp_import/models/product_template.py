# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class ProductTemplate(models.Model):
    _inherit = ['product.template']

    product_substitution_id = fields.Char(
        string='Substitution Product',
        help='Product that will serve as component in Work Order'
             ' in replacement of this one.'
    )
    preferred_supplier_id = fields.Many2one(
        comodel_name='res.partner',
        compute='_compute_preferred_supplier'
    )

    @api.depends('seller_ids')
    def _compute_preferred_supplier(self):
        """ Last supplier in supplierinfo, or company's (we need a default one) """
        for product in self:
            product.preferred_supplier_id = (
                fields.first(product.seller_ids).partner_id
                or self.env.company.partner_id
            )
