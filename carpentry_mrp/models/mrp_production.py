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
    product_id = fields.Many2one(
        domain="""[
            ('type', 'in', ['product', 'consu']),
            ('production_ok', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', company_id)
        ]"""
    )
    description = fields.Char(
        string='Description'
    )
    launch_ids = fields.Many2many(
        comodel_name='carpentry.group.launch',
        relation='mrp_production_launch_rel',
        string='Launches',
        domain="[('project_id', '=', project_id)]",
    )
    # -- for planning --
    active = fields.Boolean(
        default=True,
        string='Active?'
    )
    sequence = fields.Integer(
        string='Sequence'
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
    