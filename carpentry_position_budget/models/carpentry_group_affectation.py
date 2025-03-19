# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.osv import expression

class CarpentryGroupAffectation(models.Model):
    _inherit = ["carpentry.group.affectation"]

    #===== Fields methods =====#
    def _selection_record_res_model(self):
        """ Budget reservation are made on `launch` or `project` as `record_ref` """
        return super()._selection_record_res_model() + [
            # buget reservation (po and wo)
            ('carpentry.group.launch', 'Launch'),
            ('project.project', 'Project'),
        ]
    
    #===== Fields =====#
    budget_unit = fields.Char(compute='_compute_budget_unit_type')
    budget_type = fields.Selection(
        selection=lambda self: self.env['account.analytic.account']._fields['budget_type'].selection,
        compute='_compute_budget_unit_type',
        search='_search_budget_type',
    )

    #===== Compute =====#
    @api.depends('group_id', 'group_res_model')
    def _compute_budget_unit_type(self):
        for affectation in self:
            is_budget = affectation.group_res_model == 'account.analytic.account'
            affectation.budget_unit = is_budget and affectation.group_ref.budget_unit
            affectation.budget_type = is_budget and affectation.group_ref.budget_type
    
    def _search_budget_type(self, operator, value):
        domain = [('budget_type', '=', value)]
        analytics = self.env['account.analytic.account'].search(domain)
        return [('group_id', 'in', analytics.ids)]

    #===== Logic methods =====#
    def _get_domain_siblings(self):
        """ Budget reservation are 3d-matrix:
            one needs to filter by `group_id` (analytics) to find siblings
            (used in `_compute_quantity_remaining_to_affect()`)
        """
        domain = super()._get_domain_siblings()
        if all(x.budget_type for x in self):
            domain = expression.AND([domain, [('group_id', 'in', self.mapped('group_id'))]])
        return domain
