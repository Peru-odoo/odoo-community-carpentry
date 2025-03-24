# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from collections import defaultdict

class StockMoveLine(models.Model):
    _inherit = ['stock.move.line']

    launch_ids = fields.Many2many(related='move_id.launch_ids')

class StockMove(models.Model):
    _inherit = ['stock.move']

    launch_ids = fields.Many2many(related='picking_id.launch_ids')

    #===== CRUD =====#
    def write(self, vals):
        """ For MO's components, ensure `product_uom_qty` is >= `quantity_done`
            Because `product_uom_qty` is used for for stock forecast
            (just do like when the `stock.move` is validated)
        """
        res = super().write(vals)
        raw_material_ids = self.filtered('raw_material_production_id')
        raw_material_ids._synch_product_uom_qty_done()
        return res
    
    def _synch_product_uom_qty_done(self):
        """ Updates any `product_uom_qty` >= `quantity_done` to `quantity_done` """
        for move in self:
            if move.quantity_done > move.product_uom_qty:
                move.product_uom_qty = move.quantity_done

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
