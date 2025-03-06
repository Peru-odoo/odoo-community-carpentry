# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class ProductSubstitutionCode(models.Model):
    _name = 'product.substitution'
    _description = 'Product Substitution Code'
    _rec_name = 'substituted_code'
    _order_by = 'product_id'

    #===== Fields' method =====#
    def _default_product_id(self):
        product_id = self._context.get('default_product_id')
        product_tmpl_id = self._context.get('default_product_tmpl_id')
        return product_id or self.env['product.template'].browse(product_tmpl_id).product_variant_id.id

    #===== Fields =====#
    substituted_code = fields.Char(
        string='Substituted reference',
        required=True,
        default=lambda self: self._context.get('default_name'),
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Target Product',
        required=True,
        ondelete='cascade',
        default=_default_product_id,
    )
    default_code = fields.Char(
        related='product_id.default_code',
        string="Target Product's reference"
    )

    #===== Constrains =====#
    _sql_constraints = [(
        "substituted_code",
        "UNIQUE (substituted_code)",
        "This substituted reference is already used by another product."
    )]
    
    @api.constrains('substituted_code')
    def _constrain_code_unknown(self):
        """ `substituted_code` must not exist as `product.default_code` """
        domain = [('default_code', 'in', self.mapped('substituted_code'))]
        if self.env['product.product'].with_context(active_test=False).search(domain):
            raise exceptions.UserError(_(
                'A product reference cannot also be used as a substitution reference.\n'
                'Details: %s', self.mapped('substituted_code')
            ))

    #===== CRUD / clean =====#
    def write(self, vals):
        """ Clean substitution references not linked to any `product_id` """
        res = super().write(vals)
        if 'product_id' in vals and not self.product_id:
            self.unlink()
        return res
