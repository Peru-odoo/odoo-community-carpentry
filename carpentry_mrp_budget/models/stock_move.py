# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class StockMove(models.Model):
    _inherit = ['stock.move']

    analytic_ids = fields.Many2many(
        string='Analytic Accounts',
        comodel_name='account.analytic.account',
        compute='_compute_analytic_distribution',
        help='Automatic budget from analytic distribution model',
    )

    @api.depends('product_id', 'partner_id')
    def _compute_analytic_distribution(self):
        """ Compute budget analytics from automated analytic distribution model """
        for move in self:
            distribution = self.env['account.analytic.distribution.model']._get_distribution({
                "product_id": move.product_id.id,
                "product_categ_id": move.product_id.categ_id.id,
                "partner_id": move.partner_id.id,
                "partner_category_id": move.partner_id.category_id.ids,
                "company_id": move.company_id.id,
            })

            # synthetic: only analytic_ids (no % distribution)
            analytic_ids_ = [int(x) for x in distribution.keys()] if distribution else []
            analytic_ids = self.env['account.analytic.account'].browse(analytic_ids_)
            move.analytic_ids = analytic_ids.filtered('is_project_budget')
