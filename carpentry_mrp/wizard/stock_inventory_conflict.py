# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class StockInventoryConflict(models.TransientModel):
    _inherit = ['stock.inventory.conflict']

    def action_keep_counted_quantity(self):
        for quant in self.quant_ids:
            quant.inventory_diff_quantity = quant.inventory_quantity - quant.quantity_minus_outgoing_raw_material
        return self.quant_ids.action_apply_inventory()

    def action_keep_difference(self):
        for quant in self.quant_ids:
            quant.inventory_quantity = quant.quantity_minus_outgoing_raw_material + quant.inventory_diff_quantity
        return self.quant_ids.action_apply_inventory()
