# -*- coding: utf-8 -*-

from odoo import models, fields, api

class CarpentryPlanningCard(models.Model):
    """ So `stock.move` can be filtered by `state` """
    _inherit = ['carpentry.planning.card']

    #===== M2o fields =====#
    mrp_production_id = fields.Many2one(
        # for MO column: research by launches
        comodel_name='mrp.production',
        string='Manufacturing Orders',
    )
    stock_move_id = fields.Many2one(
        # for `stock.move` column: research by launches & state
        comodel_name='stock.move',
        string='Stock Move',
    )
    state = fields.Char(
        # for `stock.move` column, filtering by state
        search='_search_state'
    )
    
    #===== Mirror fields =====#
    name = fields.Char(compute='_compute_fields')
    description = fields.Char(compute='_compute_fields')
    product_default_code = fields.Char(compute='_compute_fields')
    product_name = fields.Char(compute='_compute_fields')
    components_availability = fields.Char(compute='_compute_fields')
    product_uom_qty = fields.Float(compute='_compute_fields')
    availability = fields.Float(compute='_compute_fields')
    
    def _get_fields(self):
        return super()._get_fields() + [
            'name', 'description', 'product_default_code', 'product_name',
            'components_availability', 'product_uom_qty', 'availability'
        ]

    #===== Compute =====#
    @api.model
    def _search_state(self, operator, value):
        domain = self._search_by_field('state', operator, value)
        return domain
