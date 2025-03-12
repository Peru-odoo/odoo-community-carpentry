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

            print('new_distrib', new_distrib)
            print('new_distrib.keys()', new_distrib and new_distrib.keys())

            # synthetic: only analytic_ids (no % distribution)
            move.analytic_ids = new_distrib and [Command.set([int(x) for x in new_distrib.keys()])]
