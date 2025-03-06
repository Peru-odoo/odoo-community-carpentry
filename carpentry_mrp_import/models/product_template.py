# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class ProductTemplate(models.Model):
    _inherit = ['product.template']

    substitution_ids = fields.One2many(
        related='product_variant_ids.substitution_ids',
        readonly=False,
        domain="[('product_id', '=', product_variant_id)]",
    )
    preferred_supplier_id = fields.Many2one(
        comodel_name='res.partner',
        compute='_compute_preferred_supplier',
    )
    substitution_product_id = fields.Many2one(
        comodel_name='product.template',
        string='Substitution product',
        compute='_compute_substitution_product_id'
    )

    #===== Substitution codes =====#
    def _get_related_fields_variant_template(self):
        """ Return a list of fields present on template and variants models and that are related"""
        return super()._get_related_fields_variant_template() + ['substitution_ids']
    
    @api.depends('product_variant_ids', 'product_variant_ids.substitution_product_id')
    def _compute_substitution_product_id(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        (self - unique_variants).substitution_product_id = False
        for template in unique_variants:
            template.substitution_product_id = (
                template.product_variant_ids.substitution_product_id.product_tmpl_id
            )

    # @api.depends('product_variant_ids', 'product_variant_ids.substitution_ids')
    # def _compute_substitution_ids(self):
    #     unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
    #     for template in unique_variants:
    #         template.substitution_ids = template.product_variant_ids.substitution_ids
    #     for template in (self - unique_variants):
    #         template.substitution_ids = False

    # def _inverse_substitution_ids(self):
    #     for template in self:
    #         if len(template.product_variant_ids) == 1:
    #             template.product_variant_ids.substitution_ids = template.substitution_ids
    
    #===== Prefered supplier =====#
    @api.depends('seller_ids')
    def _compute_preferred_supplier(self):
        """ Last supplier in supplierinfo, or company's (we need a default one) """
        for product in self:
            product.preferred_supplier_id = (
                fields.first(product.seller_ids).partner_id
                or self.env.company.partner_id
            )
    