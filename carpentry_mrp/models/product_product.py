# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.tools.float_utils import float_round
from collections import defaultdict

class ProductProduct(models.Model):
    _inherit = ['product.product']

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        """ Overwritte native method to count outgoing qties of MRP raw_material (`Consumed` column in MO) as
            already *out* in `qty_available` (On Hand) as soon as Manufacturing Order is confirmed,
            without waiting MO (and its move) to be done
        """
        res = super()._compute_quantities_dict(lot_id, owner_id, package_id, from_date, to_date)
        qties_outgoing_raw_material = self._get_qties_outgoing_raw_material(owner_id, from_date, to_date)

        for product_id, qties_dict in res.items():
            consumed = qties_outgoing_raw_material.get(product_id, 0.0)
            res[product_id]['qty_available'] -= consumed
            res[product_id]['outgoing_qty'] -= consumed
        
    #     return res

    # def _get_domain_locations(self):
    #     """ Do not count `Consumed` qties in `virtual_available` (Forecast)
    #         To switch back to standard computation, pass `qties_raw_material_included` in context
    #     """
    #     domain_quant_loc, domain_move_in_loc, domain_move_out_loc = super()._get_domain_locations()

    #     if not self._context.get('qties_raw_material_included'):
    #         domain_move_out_loc = [('raw_material_production_id', '=', False)] + domain_move_out_loc

    #     return domain_quant_loc, domain_move_in_loc, domain_move_out_loc

    def _get_qties_outgoing_raw_material(self, owner_id=None, from_date=False, to_date=False):
        """ Inspired from native `_compute_quantities_dict()`
            Returns `quantity_done` of pending moves of MO's raw materials (components)

            :return: dict like `{product_id: quantity_done}`
        """
        # self = self.with_context(qties_raw_material_included=True)
        _, _, domain_move_out_loc = self._get_domain_locations()
        domain_move_out = (
            [('product_id', 'in', self.ids), ('raw_material_production_id', '!=', False)]
            + domain_move_out_loc
        )

        if owner_id is not None:
            domain_move_out += [('restrict_partner_id', '=', owner_id)]
        if from_date:
            domain_move_out += [('date', '>=', from_date)]
        if to_date:
            domain_move_out += [('date', '<=', to_date)]

        domain_move_out_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_out
        moves_out_res = self.env['stock.move'].with_context(active_test=False)._read_group(
            domain=domain_move_out_todo,
            fields=['product_id', 'quantity_done:sum'],
            groupby=['product_id', 'product_uom'], # `product_uom` needed to convert with `_compute_quantity()`
            orderby='id',
            lazy=False
        )
        product_uoms = self.env['uom.uom'].sudo().browse([item['product_uom'][0] for item in moves_out_res])
        products = self.env['product.product'].sudo().browse([item['product_id'][0] for item in moves_out_res])
        
        res = defaultdict(int)
        for item in moves_out_res:
            product_uom = product_uoms.browse(item['product_uom'][0])
            product = products.browse(item['product_id'][0])

            qty_done = product_uom._compute_quantity(item['quantity_done'], product.uom_id, rounding_method='HALF-UP')
            res[product.id] += float_round(qty_done, precision_rounding=product.uom_id.rounding)

        return res
