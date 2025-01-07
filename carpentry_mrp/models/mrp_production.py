# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class ManufacturingOrder(models.Model):
    _inherit = ['mrp.production']
    
    # domaine des produits move_byproduct_ids
    # product_id computed: *first* de move_byproduct_ids
    # cacher product_id et qty du haut du form MO
    product_id = fields.Many2one(
        domain="""[
            ('type', 'in', ['product', 'consu']),
            ('production_ok', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', company_id)
        ]"""
    )
    # product_qty = fields.Float(
    #     readonly=True
    # )
    active = fields.Boolean(
        # for planning
        default=True
    )


    #===== Compute =====#
    # @api.depends('move_finished_ids')
    # def _compute_product_qty(self):
    #     res = super()._compute_product_qty()

    #     for order in self:
    #         order.product_qty = len(order.move_finished_ids)
        
    #     return res

    # @api.depends('move_finished_ids')
    # def _compute_move_byproduct_ids(self):
    #     """ Actually show all product in `By-Products` tab, including the main one """
    #     res = super()._compute_move_byproduct_ids()

    #     for order in self:
    #         order.move_byproduct_ids = order.move_finished_ids
        
    #     return res
    