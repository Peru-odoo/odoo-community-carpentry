# -*- coding: utf-8 -*-

from odoo import api, models, fields, exceptions, _, Command

class StockPicking(models.Model):
    _inherit = ['stock.picking']

    #===== Fields =====#
    description = fields.Char(
        string='Description',
        compute='_compute_launch_ids_description',
        store=True,
        readonly=False,
    )
    launch_ids = fields.Many2many(
        string='Launches',
        comodel_name='carpentry.group.launch',
        compute='_compute_launch_ids_description',
        store=True,
        readonly=False,
        domain="[('project_id', '=', project_id)]"
    )
    mrp_production_ids = fields.One2many(
        # remove related so when modified, we link the picking to the MO's procurement group
        inverse='_inverse_mrp_production_ids',
        domain="[('project_id', '=', project_id)]"
    )

    #===== Compute =====#
    @api.depends('mrp_production_ids', 'purchase_id')
    def _compute_launch_ids_description(self):
        for picking in self:
            po = picking.purchase_id
            mo = picking.mrp_production_ids

            picking.launch_ids = po.launch_ids | mo.launch_ids
            if po or len(mo) == 1:
                picking.description = po.description if po else mo.description

    @api.model
    def _search_launch_ids(self, operator, value):
        return ['|',
            ('mrp_production_ids.launch_ids', operator, value),
            ('purchase_id.launch_ids', operator, value),
        ]

    # TO BE TESTED : inverse of related
    def _inverse_mrp_production_ids(self):
        """ Allow update of `mrp_production_ids` from the picking """
        for picking in self:
            group = fields.first(picking.mrp_production_ids.procurement_group_id)
            group.mrp_production_ids = [Command.link(x.id) for x in picking.mrp_production_ids]
            picking.group_id = group
