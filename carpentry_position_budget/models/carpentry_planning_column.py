# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.osv import expression

def human_readable(num, scale=1000.0):
    for unit in ("", "k", "m"):
        if abs(num) < scale:
            return f"{num:3.0f}{unit}"
        num /= scale
    return f"{num:.0f}M"

class CarpentryPlanningColumn(models.Model):
    _inherit = ["carpentry.planning.column"]

    budget_type = fields.Selection(
        selection=lambda self: self.env['account.analytic.account'].fields_get()['budget_type']['selection'],
        string='Budget Type',
    )

    #===== RPC calls (columns' sub-headers) =====#
    def get_headers_data(self, launch_id_):
        """ Add budget information to planning's columns headers """
        res = super().get_headers_data(launch_id_)
        return res
    
        if not self.mapped('budget_type'):
            return res
        
        analytics = self.env['account.analytic.account'].search([('is_project_budget', '=', True)])

        # 1. Retrieve all *available (brut)*, *reserved budget* and *expense* for this launch
        mapped_available = self.env['carpentry.budget.available']._get_groupby(self, [launch_id_], 'budget_type')
        mapped_reserved, mapped_expense = self.env['carpentry.budget.expense']._get_groupby(self, [launch_id_], 'budget_type')
        # 2. ratio répartition % / dépense lancement
        #   dans chaque section / budget_type selon budget réservé,
        #   groupé pour toutes les sections par niveau du budget_type

        # 2. Compute data per column
        for column in self:
            budget_type = column.budget_type
            if not budget_type:
                continue

            column_analytics = analytics.filtered(lambda x: x.budget_type == column.budget_type)
            is_hour = set(column_analytics.mapped('budget_unit')) == {'h'}

            res[column.id]['budget'] = {
                'unit': 'h' if is_hour else '€',
                'expense': human_readable(mapped_expense.get(budget_type)),
                'reserved': human_readable(mapped_reserved.get(budget_type)),
                'available': human_readable(mapped_available.get(budget_type)),
            }

        return res
