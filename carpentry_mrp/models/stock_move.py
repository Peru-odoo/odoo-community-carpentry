# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from collections import defaultdict

class StockMoveLine(models.Model):
    _inherit = ['stock.move.line']

    launch_ids = fields.Many2many(related='move_id.launch_ids')

class StockMove(models.Model):
    _inherit = ['stock.move']

    raw_material_production_id_state = fields.Selection(related='raw_material_production_id.state')
    launch_ids = fields.Many2many(related='picking_id.launch_ids')

    # # ===== V2 =====
    # # ===== Constrain =====#
    # @api.constrains('product_id')
    # def _constrain_component_single_product(self):
    #     if self._context.get('ignore_constrain_component_single_product'):
    #         return
        
    #     for move in self:
    #         mo = move.raw_material_production_id
    #         if mo:
    #             siblings = mo.move_raw_ids - move
    #             if move.product_id in siblings.product_id:
    #                 raise exceptions.UserError(_(
    #                     'The product %s is already in the list of the components.'
    #                     ' Please rather update the existing line.',
    #                     move.product_id.display_name
    #                 ))

    # #===== CRUD & Logic =====#
    # def write(self, vals):
    #     """ Move to `done` the components of MO as soon as `quantity_done` is filled """
    #     res = super().write(vals)
    #     if 'quantity_done' in vals:
    #         self = self.with_context(ignore_constrain_component_single_product=True)
    #         moves_mrp = self.filtered(lambda x: x.raw_material_production_id and x.quantity_done > 0)
    #         moves_mrp._action_done_mrp_carpentry()
    #     return res
    
    # def _action_done_mrp_carpentry(self):
    #     """ Inspired from native `_action_done()` but much simplier:
    #         - don't cancel if qty_done<=0
    #         - don't create extra move
    #         - don't create backorders
    #         - don't split or merge
    #         => Done `move_raw_ids` are just 'done' and stay editable from the MO
    #     """
    #     print('=== _action_done_mrp_carpentry ===')
    #     moves = self.filtered(lambda move: move.state == 'draft')._action_confirm()  # MRP allows scrapping draft moves
    #     moves = self
    #     moves = (self | moves).exists().filtered(lambda x: x.state not in ('done', 'cancel'))
    #     moves._check_company()

    #     if any(ml.package_id and ml.package_id == ml.result_package_id for ml in moves.move_line_ids):
    #         self.env['stock.quant']._unlink_zero_quants()
        
    #     moves.write({'state': 'done', 'date': fields.Datetime.now()})
        
    #     move_dests_per_company = defaultdict(lambda: self.env['stock.move'])
    #     for move_dest in moves.move_dest_ids:
    #         move_dests_per_company[move_dest.company_id.id] |= move_dest
    #     for company_id, move_dests in move_dests_per_company.items():
    #         move_dests.sudo().with_company(company_id)._action_assign()
        
    #     return moves

    # # def _action_confirm(self, merge=True, merge_into=False):
    # #     """ Called when creating move backorders within `stock_move._action_done()`
    # #         (when `quantity_done` < `product_uom_qty).
    # #         But for MO's components, we don't want several lines of same product.
    # #         This may happen a lot since we validated move as soon as `quantity_done` is
    # #         changed (cf. `write()`)
    # #         => re-merge `move_raw_ids`
    # #     """
    # #     # move_raw_ids = self.filtered('raw_material_production_id')
    # #     # other_moves = self - move_raw_ids

    # #     # return (
    # #     #     super(StockMove, move_raw_ids)._action_confirm(merge=True, merge_into) |
    # #     #     super(StockMove, other_moves )._action_confirm(merge=merge, merge_into)
    # #     # )

    # #     print('=== _action_confirm ===')
    # #     return super()._action_confirm(merge, merge_into)
    
    # #===== Compute =====#
    # @api.depends('quantity_done', 'product_uom_qty')
    # def _compute_is_done(self):
    #     """ Used in `order_by` => display first the undone moves """
    #     for move in self:
    #         move.is_done = (move.state in ('done', 'cancel')) and (move.quantity_done == move.product_uom_qty)

    #===== Buttons =====#
    def unlink(self):
        """ *Delete* button is always displayed for `move_raw_ids` and behaves like:
            - unlinks `move_raw_ids` if possible ;
            - else (if move is `done`), sets qty to 0 instead
        """
        move_raw_ids = self.filtered('raw_material_production_id')
        to_cancel = move_raw_ids.filtered(lambda x: x.state != 'cancel')
        to_unlink = self - to_cancel

        # Unlink normally if possible (or if not raw material)
        super(StockMove, to_unlink).unlink()
        
        if to_cancel:
            # Not cancellable components: quantity_done = 0
            to_zero = to_cancel.filtered(lambda x: x.state == 'done')
            to_zero.quantity_done = 0.0

            # If components can be canceled: cancel & delete
            (to_cancel - to_zero)._action_cancel()
            super(StockMove, to_cancel - to_zero).unlink()










    # ==== V1 =====
    # def _action_done_components_no_backorder(self):
    #     """ If `move_raw_ids` are validated when `quantity_done` < `product_uom`,
    #         it natively split the move with a backorder. We don't want it: this method
    #         re-writes native `_action_done` without creating any backorder
    #     """
    #     moves = self.filtered(lambda move: move.state == 'draft')._action_confirm()
    #     moves_todo = (self | moves).exists().filtered(lambda x: x.state not in ('done', 'cancel'))
    #     moves_todo._check_company()

    #     # The backorder moves are not yet in their own picking. We do not want to check entire packs for those
    #     # ones as it could messed up the result_package_id of the moves being currently validated
    #     backorder_moves.with_context(bypass_entire_pack=True)._action_confirm(merge=False)
    #     if cancel_backorder:
    #         backorder_moves.with_context(moves_todo=moves_todo)._action_cancel()
    #     moves_todo.mapped('move_line_ids').sorted()._action_done()
    #     # Check the consistency of the result packages; there should be an unique location across
    #     # the contained quants.
    #     for result_package in moves_todo\
    #             .mapped('move_line_ids.result_package_id')\
    #             .filtered(lambda p: p.quant_ids and len(p.quant_ids) > 1):
    #         if len(result_package.quant_ids.filtered(lambda q: not float_is_zero(abs(q.quantity) + abs(q.reserved_quantity), precision_rounding=q.product_uom_id.rounding)).mapped('location_id')) > 1:
    #             raise UserError(_('You cannot move the same package content more than once in the same transfer or split the same package into two location.'))
    #     if any(ml.package_id and ml.package_id == ml.result_package_id for ml in moves_todo.move_line_ids):
    #         self.env['stock.quant']._unlink_zero_quants()
    #     picking = moves_todo.mapped('picking_id')
    #     moves_todo.write({'state': 'done', 'date': fields.Datetime.now()})

    #     new_push_moves = moves_todo.filtered(lambda m: m.picking_id.immediate_transfer)._push_apply()
    #     if new_push_moves:
    #         new_push_moves._action_confirm()
    #     move_dests_per_company = defaultdict(lambda: self.env['stock.move'])
    #     for move_dest in moves_todo.move_dest_ids:
    #         move_dests_per_company[move_dest.company_id.id] |= move_dest
    #     for company_id, move_dests in move_dests_per_company.items():
    #         move_dests.sudo().with_company(company_id)._action_assign()

    #     # We don't want to create back order for scrap moves
    #     # Replace by a kwarg in master
    #     if self.env.context.get('is_scrap'):
    #         return moves_todo

    #     if picking and not cancel_backorder:
    #         backorder = picking._create_backorder()
    #         if any([m.state == 'assigned' for m in backorder.move_ids]):
    #            backorder._check_entire_pack()
    #     return moves_todo
