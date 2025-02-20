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
    # -- for planning --
    active = fields.Boolean(default=True, string='Active?')
    sequence = fields.Integer(string='Sequence')
    
    #===== Compute =====#
    def _action_cancel(self):
        """ Forces the cancelling of `done` move_raw_ids """
        super()._action_cancel()
        move_done = self.move_raw_ids.filtered(lambda x: x.state in ('done'))
        move_done.quantity_done = 0.0


    # def action_confirm(self):
    #     """ When confirming, set `move_raw_ids` to done so any changes in `quantity_done`
    #         is taken into account in real time
    #     """
    #     res = super().action_confirm()
    #     self._post_inventory(cancel_backorder=True, components=True, finished=False)
    #     return res
    
    # def _autoconfirm_production(self):
    #     """ Called when move_raw_ids are added to the mrp.production
    #         after the initial `action_confirm()`
    #     """
    #     res = super()._autoconfirm_production()
    #     self._post_inventory(cancel_backorder=True, components=True, finished=False)
    #     return res

    # def _post_inventory(self, cancel_backorder=False, components=True, finished=True):
    #     """ Overwrite _post_inventory to split `move_raw_ids` and `move_finished_ids` """
    #     if components: # [ADDED]
    #         # skip `moves_not_to_do`
    #         moves_to_do = self.move_raw_ids.filtered(lambda x: x.state != 'cancel')
    #         for move in moves_to_do:
    #             if move.product_qty == 0.0 and move.quantity_done > 0:
    #                 move.product_uom_qty = move.quantity_done
    #         moves_to_do._action_done(cancel_backorder=cancel_backorder)
    #         moves_to_do = self.move_raw_ids.filtered(lambda x: x.state == 'done')
    #         # Create a dict to avoid calling filtered inside for loops.
    #         moves_to_do_by_order = defaultdict(lambda: self.env['stock.move'], [
    #             (key, self.env['stock.move'].concat(*values))
    #             for key, values in tools_groupby(moves_to_do, key=lambda m: m.raw_material_production_id.id)
    #         ])
        
    #     for order in self:
    #         if finished: # [ADDED]
    #             finish_moves = order.move_finished_ids.filtered(lambda m: m.product_id == order.product_id and m.state not in ('done', 'cancel'))
    #             # the finish move can already be completed by the workorder.
    #             for move in finish_moves:
    #                 if move.quantity_done:
    #                     continue
    #                 move._set_quantity_done(float_round(order.qty_producing - order.qty_produced, precision_rounding=order.product_uom_id.rounding, rounding_method='HALF-UP'))
    #                 move.move_line_ids.write(order._prepare_finished_extra_vals())
    #         if components: # [ADDED]
    #             # workorder duration need to be set to calculate the price of the product
    #             for workorder in order.workorder_ids:
    #                 if workorder.state not in ('done', 'cancel'):
    #                     workorder.duration_expected = workorder._get_duration_expected()
    #                 if workorder.duration == 0.0:
    #                     workorder.duration = workorder.duration_expected
    #                     workorder.duration_unit = round(workorder.duration / max(workorder.qty_produced, 1), 2)
    #             order._cal_price(moves_to_do_by_order[order.id])
        
    #     if finished: # [ADDED]
    #         moves_to_finish = self.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
    #         moves_to_finish = moves_to_finish._action_done(cancel_backorder=cancel_backorder)
    #         self.action_assign()
        
    #     if finished and components: # [ADDED]
    #         for order in self:
    #             consume_move_lines = moves_to_do_by_order[order.id].mapped('move_line_ids')
    #             order.move_finished_ids.move_line_ids.consume_line_ids = [(6, 0, consume_move_lines.ids)]
        
    #     return True

    # #===== Compute =====#
    # # @api.depends('move_finished_ids')
    # # def _compute_product_qty(self):
    # #     res = super()._compute_product_qty()

    # #     for order in self:
    # #         order.product_qty = len(order.move_finished_ids)
        
    # #     return res

    # # @api.depends('move_finished_ids')
    # # def _compute_move_byproduct_ids(self):
    # #     """ Actually show all product in `By-Products` tab, including the main one """
    # #     res = super()._compute_move_byproduct_ids()

    # #     for order in self:
    # #         order.move_byproduct_ids = order.move_finished_ids
        
    # #     return res
    