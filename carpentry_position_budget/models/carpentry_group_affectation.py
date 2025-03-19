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
    uom_name = fields.Char(compute='_compute_uom_name_is_budget_timesheetable')
    is_budget = fields.Boolean(compute='_compute_uom_name_is_budget_timesheetable')
    timesheetable = fields.Boolean(compute='_compute_uom_name_is_budget_timesheetable')

    #===== Compute =====#
    @api.depends('group_id', 'group_res_model')
    def _compute_uom_name_is_budget_timesheetable(self):
        for affectation in self:
            # uom_name
            affectation.uom_name = 'h' if affectation.group_ref.timesheetable else '€'

            # is_budget
            is_budget = affectation.group_res_model == 'account.analytic.account'
            affectation.is_budget = is_budget

            # timesheetable
            affectation.timesheetable = is_budget and affectation.group_ref.timesheetable
            
    #===== Logic methods =====#
    def _get_domain_siblings(self):
        """ Budget reservation are 3d-matrix:
            one needs to filter by `group_id` (analytics) to find siblings
            (used in `_compute_quantity_remaining_to_affect()`)
        """
        domain = super()._get_domain_siblings()
        if all(x.is_budget for x in self):
            domain = expression.AND([domain, [('group_id', 'in', self.mapped('group_id'))]])
        return domain
