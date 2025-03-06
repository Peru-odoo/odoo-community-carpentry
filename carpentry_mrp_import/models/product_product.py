# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class ProductProduct(models.Model):
    _inherit = ['product.product']

    substitution_ids = fields.One2many(
        comodel_name='product.substitution',
        inverse_name='product_id',
        string='Substituted references',
        groups='mrp.group_mrp_user',
        domain="[('product_id', '=', id)]",
        help='References replaced by the current product when importing'
             ' Components in Manufacturing Orders.'
    )
    substitution_product_id = fields.Many2one(
        comodel_name='product.product',
        string='Substitution product',
        compute='_compute_substitution_product_id'
    )


    #===== Constrain =====#
    @api.constrains('substitution_ids')
    def _constrain_subsitution_chained(self):
        for product in self:
            if product.substitution_ids and product.substitution_product_id:
                raise exceptions.ValidationError(_(
                    "A product used as substitution for other references cannot itself have its"
                    " internal reference substituted. Product: %s", product.display_name
                ))

    #===== Compute =====#
    def _compute_substitution_product_id(self):
        """ Finds subsitution product if the current one is substituted by another product
            (reverse logic of `substitution_ids`)
        """
        domain = [('substituted_code', 'in', self.mapped('default_code'))]
        mapped_substitution_ids = {
            x.substituted_code: x.product_id
            for x in self.env['product.substitution'].search(domain)
        }
        for product in self:
            product.substitution_product_id = mapped_substitution_ids.get(product.default_code)
