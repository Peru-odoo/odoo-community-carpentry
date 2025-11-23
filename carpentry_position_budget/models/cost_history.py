# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class HrEmployeeTimesheetCostHistory(models.Model):
    _inherit = ["hr.employee.timesheet.cost.history"]

    @api.model_create_multi
    def create(self, vals_list):
        histories = super().create(vals_list)
        histories._update_budget_totals()
        return histories

    def write(self, vals):
        res = super().write(vals)
        fields = ('analytic_account_id', 'starting_date', 'date_to', 'hourly_cost')
        if any(x in vals for x in fields):
            self._update_budget_totals()
        return res
    
    def unlink(self):
        aacs = self.analytic_account_id
        res = super().unlink()
        if aacs:
            self._update_budget_totals(aacs)
        return res
    
    def copy(self, vals={}):
        res = super().copy(vals)
        self._update_budget_totals()
        return res
    
    def _update_budget_totals(self, aacs=None):
        """ On valuattion changes, update:
            * records' totals (budget reservations/expenses)
            * reservation's valued amount
        """
        aacs = aacs or self.analytic_account_id
        if not aacs:
            return

        # update reservations
        reservations = self.env['carpentry.budget.reservation'].search(
            [('analytic_account_id' , 'in', aacs.ids)]
        )
        if not reservations:
            return
        reservations._compute_amount_reserved_valued()

        # update records
        record_fields = reservations._get_record_fields()
        for field in record_fields:
            records = reservations[field]
            if records:
                rg_result = records._get_rg_result_expense()
                records._compute_total_budget_reserved(rg_result=rg_result)
                records._compute_total_expense_gain(rg_result=rg_result)
