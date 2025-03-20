# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.tools.misc import groupby as tools_groupby
from collections import defaultdict

class ManufacturingOrder(models.Model):
    _inherit = ['mrp.production']
    _rec_name = 'display_name'
    _rec_names_search = ['name', 'description']

    #===== Fields methods =====#
    def _compute_display_name(self):
        for mo in self:
            mo.display_name = '[{}] {}' . format(mo.name, mo.description) if mo.description else mo.name
    
    #===== Fields =====#
    description = fields.Char(string='Description')
    launch_ids = fields.Many2many(
        comodel_name='carpentry.group.launch',
        relation='mrp_production_launch_rel',
        string='Launches',
        domain="[('project_id', '=', project_id)]",
    )
    purchase_ids = fields.Many2many(
        string='Related Purchase Orders',
        related='launch_ids.purchase_ids'
    )
    purchase_order_count = fields.Integer(
        # from `purchase_mrp`
        string='Count of linked PO'
    )
    # -- for planning --
    active = fields.Boolean(default=True, string='Active?')
    sequence = fields.Integer(string='Sequence')
    
    #===== Linked Purchase Orders =====#
    @api.depends('launch_ids')
    def _compute_purchase_order_count(self):
        for production in self:
            production.purchase_order_count = len(production._get_purchase_ids())
    
    def _get_purchase_ids(self):
        return (
            self.procurement_group_id.stock_move_ids.created_purchase_line_id.order_id |
            self.procurement_group_id.stock_move_ids.move_orig_ids.purchase_line_id.order_id |
            self.launch_ids.purchase_ids
        )
    
    def action_view_purchase_orders(self):
        return super().action_view_purchase_orders() | {
            'domain': [('id', 'in', self._get_purchase_ids().ids)]
        }

    #===== Logics =====#
    def _action_cancel(self):
        """ Forces the cancelling of `done` move_raw_ids """
        super()._action_cancel()
        move_done = self.move_raw_ids.filtered(lambda x: x.state in ('done'))
        move_done.quantity_done = 0.0
