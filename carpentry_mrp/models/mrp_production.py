# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class ManufacturingOrder(models.Model):
    _inherit = ['mrp.production']
    _rec_name = 'display_name'

    #===== Fields methods =====#
    def _compute_display_name(self):
        for mo in self:
            mo.display_name = '[{}] {}' . format(self.name, self.description) if self.description else self.name
    
    #===== Fields =====#
    description = fields.Char(
        string='Description'
    )
    product_id = fields.Many2one(
        domain="""[
            ('type', 'in', ['product', 'consu']),
            ('production_ok', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', company_id)
        ]"""
    )
    active = fields.Boolean(
        # for planning
        default=True
    )


    #===== Logics methods =====#
    def _prepare_procurement_group_vals(self, values):
        """ And `production_id` on picking via the procurement group """
        return super()._prepare_procurement_group_vals(values) | {
            'production_id': self.id
        }


    
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
    