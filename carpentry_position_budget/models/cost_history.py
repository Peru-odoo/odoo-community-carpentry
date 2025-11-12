# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class HrEmployeeTimesheetCostHistory(models.Model):
    _inherit = ["hr.employee.timesheet.cost.history"]

    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)._update_budget_totals()

    def write(self, vals):
        res = super().write(vals)
        fields = ('starting_date', 'date_to', 'hourly_cost')
        if any(x in vals for x in fields):
            self._update_budget_totals()
        return res
    
    def unlink(self):
        aacs = self.analytic_account_ids
        res = super().unlink()
        self._update_budget_totals(aacs)
        return res
    
    def copy(self, vals={}):
        res = super().copy(vals)
        self._update_budget_totals()
        return res
    
    def _update_budget_totals(self, aacs=None):
        """ Updated totals of records' budget reservations/expenses
            on changes of valuation
        """
        aacs = aacs or self.analytic_account_id
        reservations = self.env['carpentry.budget.reservation'].search(
            [('analytic_account_id' , 'in', aacs.ids)]
        )
        record_fields = reservations._get_record_fields()
        for field in record_fields:
            records = reservations[field]
            if records:
                records._compute_total_budget_reserved()
                records._compute_total_expense_gain()
    