# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.osv import expression

class CarpentryGroupLaunch(models.Model):
    _inherit = ['carpentry.group.launch']
    
    #===== Fields =====#
    production_ids = fields.Many2many(
        # inverse m2m with `mrp.production`
        comodel_name='mrp.production',
        relation='mrp_production_launch_rel',
        string='Manufacturing Orders',
        domain="[('project_id', '=', project_id)]",
    )
    picking_ids = fields.Many2many(
        # inverse m2m with `stock.picking`
        comodel_name='stock.picking',
        string='Pickings',
        relation='stock_picking_launch_rel',
        domain="[('project_id', '=', project_id)]",
    )
    move_ids = fields.One2many(
        string='Stock Moves',
        comodel_name='stock.move',
        compute='_compute_move_ids',
        search='_search_move_ids',
    )
    pending_move_ids = fields.One2many(
        string='Pending Stock Moves',
        comodel_name='stock.move',
        compute='_compute_move_ids',
        readonly=True,
    )

    #===== Compute =====#
    @api.depends('production_ids.move_raw_ids', 'picking_ids.move_ids')
    def _compute_move_ids(self):
        """ Compute `move_ids` and `pending_move_ids`
            from `production_ids` *OR* `picking_ids`
        """
        for launch in self:
            launch.move_ids = launch.production_ids.move_raw_ids | launch.picking_ids.move_ids
            launch.pending_move_ids = launch.move_ids.filtered(lambda x: x.state in ('waiting', 'confirmed', 'partially_available'))
    def _search_move_ids(self, operator, value):
        """ Search `move_ids` from `production_ids` *OR* `picking_ids` """
        return ['|',
            ('production_ids.move_raw_ids', operator, value),
            ('picking_ids.move_ids', operator, value),
        ]
