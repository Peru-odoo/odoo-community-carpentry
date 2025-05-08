# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class StockMove(models.Model):
    _name = 'stock.move'
    _inherit = ['stock.move', 'analytic.mixin']

    analytic_distribution = fields.Json(store=False)
    analytic_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        compute='_compute_analytic_distribution',
        string='Analytic Accounts'
    )
    price_unit = fields.Float(
        help="For permanent valuation. Product cost at move's confirmation.",
    )
    standard_price = fields.Float(
        related='product_id.standard_price',
        string='Product Cost',
        help='For temporary valuation. Current product cost.'
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
    )

    @api.depends('product_id', 'partner_id')
    def _compute_analytic_distribution(self):
        """ Computed field `analytic_distribution` (intermediate Manufacturing Order) """
        for move in self:
            distribution = self.env['account.analytic.distribution.model']._get_distribution({
                "product_id": move.product_id.id,
                "product_categ_id": move.product_id.categ_id.id,
                "partner_id": move.partner_id.id,
                "partner_category_id": move.partner_id.category_id.ids,
                "company_id": move.company_id.id,
            })
            new_distrib = distribution or move.analytic_distribution
            move.analytic_distribution = new_distrib

            # synthetic: only analytic_ids (no % distribution)
            move.analytic_ids = self._get_analytic_ids()

    def _get_analytic_ids(self):
        """ Compute analytics records from json `analytic_distribution` """
        analytic_ids_ = []
        for analytic in self:
            distrib = analytic.analytic_distribution
            if distrib:
                analytic_ids_ += [int(x) for x in distrib.keys()]
        return self.env['account.analytic.account'].sudo().browse(analytic_ids_)
