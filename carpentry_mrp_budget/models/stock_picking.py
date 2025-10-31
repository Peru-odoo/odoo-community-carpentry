# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class StockPicking(models.Model):
    """ Budget Reservation on pickings """
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'carpentry.budget.mixin']
    _carpentry_budget_notebook_page_xpath = '//page[@name="operations"]'
    _carpentry_budget_last_valuation_step = _('products revaluation')

    #====== Fields ======#
    reservation_ids = fields.One2many(domain=[('section_res_model', '=', _name)])
    expense_ids = fields.One2many(domain=[('section_res_model', '=', _name)])
    budget_analytic_ids = fields.Many2many(
        relation='carpentry_budget_picking_analytic_rel',
        column1='picking_id',
        column2='analytic_id',
    )
    
    #====== Analytic mixin ======#
    @api.onchange('project_id')
    def _cascade_project_to_line_analytic_distrib(self, new_project_id=None):
        return super()._cascade_project_to_line_analytic_distrib(new_project_id)
    
    #===== Affectations =====#
    def _compute_state(self):
        """ Ensure `affectations_ids.active` follows `stock_picking.state`,
            which is a computed stored field and thus not catched in `write`
        """
        res = super()._compute_state()
        self.reservation_ids._compute_section_fields()
        return res

    #===== Budget reservation configuration =====#
    def _get_budget_types(self):
        return ['goods', 'other']
    
    def _get_fields_budget_reservation_refresh(self):
        return super()._get_fields_budget_reservation_refresh() + [
            'move_ids', 'state',
        ]
    
    def _should_value_budget_reservation(self):
        return True

    def _depends_can_reserve_budget(self):
        return super()._depends_can_reserve_budget() + ['picking_type_code', 'purchase_id']
    def _get_domain_can_reserve_budget(self):
        """ Prevent budget reservation on picking coming from:
            - internal, incoming, fab (returns from sconstruction field)
            - purchase orders
            - manufacturing orders
        """
        return super()._get_domain_can_reserve_budget() + [
            ('purchase_id', '=', False),
            ('picking_type_code', '=', 'outgoing'),
        ]
    
    def _get_domain_is_temporary_gain(self):
        return [('state', '!=', 'done'),]

    #===== Compute: date & amounts =====#
    @api.depends('scheduled_date', 'date_done')
    def _compute_date_budget(self):
        for picking in self:
            if picking.state == 'done':
                picking.date_budget = picking.date_done
            else:
                picking.date_budget = picking.scheduled_date
        return super()._compute_date_budget()
