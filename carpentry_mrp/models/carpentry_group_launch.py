# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class CarpentryGroupLaunch(models.Model):
    _inherit = ['carpentry.group.launch']
    
    production_ids = fields.Many2many(
        comodel_name='mrp.production',
        relation='mrp_production_launch_rel',
        string='Manufacturing Orders',
    )
    picking_ids = fields.Many2many(
        string='Pickings',
        comodel_name='stock.picking',
        compute='_compute_picking_ids',
        search='_search_picking_ids',
    )
    move_ids = fields.One2many(related='picking_ids.move_ids')

    @api.depends('purchase_ids', 'production_ids')
    def _compute_picking_ids(self):
        for launch in self:
            launch.picking_ids = (
                launch.purchase_ids.picking_ids |
                launch.production_ids.picking_ids
            )
    @api.model
    def _search_picking_ids(self, operator, value):
        return ['|',
            ('purchase_ids.picking_ids', operator, value),
            ('production_ids.picking_ids', operator, value),
        ]
