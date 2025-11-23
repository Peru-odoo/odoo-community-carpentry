# -*- coding: utf-8 -*-

from odoo import models, fields
from collections import defaultdict

def human_readable(num, scale=1000.0):
    return round(num) if num else 0.0
    # for unit in ("", "k", "m"):
    #     if abs(num) < scale:
    #         return f"{num:3.0f}{unit}"
    #     num /= scale
    # return f"{num:.0f}M"

class CarpentryPlanningColumn(models.Model):
    _inherit = ["carpentry.planning.column"]

    budget_types = fields.Char(
        string='Budget Type(s)',
        help='Technical names of budget types separated by a coma',
    )

    #===== RPC calls (columns' sub-headers) =====#
    def get_headers_data(self, launch_id_):
        """ Add budget information to planning's columns headers """
        res = super().get_headers_data(launch_id_)
        
        budget_types = list(set([
            budget_type
            for budget_types_char in self.filtered('budget_types').mapped('budget_types')
            for budget_type in budget_types_char.split(',')
        ]))
        if not budget_types:
            return res
        
        # 1. Available (brut)
        domain_budget = [('budget_type', 'in', budget_types)]
        domain = [('launch_id', '=', launch_id_)] + domain_budget
        rg_available = self.env['carpentry.budget.available']._read_group(
            domain=domain, groupby=['budget_type'], fields=['amount_subtotal:sum'],
        )
        mapped_available = {x['budget_type']: x['amount_subtotal'] for x in rg_available}

        # 2. Reserved (brut or valued)
        # + for expense distribution per launch (only)
        BudgetMixin = self.env['carpentry.budget.mixin']
        fields = ['amount_reserved', 'amount_reserved_valued']
        budget_fields = ['project_id', 'launch_id', 'budget_type']
        rg_reserved = self.env['carpentry.budget.reservation']._read_group(
            domain=domain, groupby=budget_fields, lazy=False,
            fields=[field + ':sum' for field in fields],
        )
        mapped_reserved = {
            BudgetMixin._get_key(vals=x, mode='planning'):
            {field: x[field] for field in fields}
            for x in rg_reserved
        }
        mapped_ratio = BudgetMixin._get_budget_distribution({
            key: vals['amount_reserved_valued']
            for key, vals in mapped_reserved.items()
        })

        # 3. Expense, to be distributed by launch as per mapped_ratio
        fields = ['amount_expense', 'amount_expense_valued']
        rg_expense = self.env['carpentry.budget.expense']._read_group(
            domain=domain_budget, groupby=['budget_type'],
            fields=[field + ':sum' for field in fields],
        )
        mapped_expense = {
            x['budget_type']: {field: x[field] for field in fields}
            for x in rg_expense
        }

        # 4. Format data per column
        project_id = self.env['carpentry.group.launch'].browse(launch_id_).project_id.id
        budget_types_workforce = self.env['account.analytic.account']._get_budget_type_workforce()
        for column in self.filtered('budget_types'):
            # valued ?
            budget_types = column.budget_types.split(',')
            is_hour = all([
                budget_type in budget_types_workforce
                for budget_type in budget_types
            ])
            valued = '' if is_hour else '_valued'

            # sums
            available, reserved, expense = 0.0, 0.0, 0.0
            for budget_type in budget_types:
                available += mapped_available.get(budget_type, 0.0)

                key_budget = (project_id, launch_id_, budget_type)
                reserved += mapped_reserved.get(key_budget, {}).get('amount_reserved' + valued, 0.0)
                ratio = mapped_ratio.get(key_budget, 0.0)
                expense += mapped_expense.get(budget_type, {}) .get('amount_expense'  + valued, 0.0) * ratio

            res[column.id]['budget'] = {
                'unit': 'h' if is_hour else '€',
                'available': human_readable(available),
                'reserved': human_readable(reserved),
                'expense': human_readable(expense),
            }

        return res
