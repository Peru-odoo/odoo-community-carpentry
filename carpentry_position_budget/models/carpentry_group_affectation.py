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
    uom_name = fields.Char(compute='_compute_uom_name')
    is_budget = fields.Boolean(compute='_compute_is_budget', default=False)

    #===== Compute =====#
    @api.depends('group_id')
    def _compute_uom_name(self):
        for affectation in self:
            affectation.uom_name = 'h' if affectation.group_ref.timesheetable else '€'

    def _compute_is_budget(self):
        section_res_models = self._get_budget_section_res_model()
        for affectation in self:
            affectation.is_budget = affectation.section_res_model in section_res_models
    def _get_budget_section_res_model(self):
        """ To be inherited """
        return []

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
