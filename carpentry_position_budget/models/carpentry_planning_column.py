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
        domain = [('launch_id', '=', launch_id_), ('budget_type', 'in', budget_types)]
        rg_available = self.env['carpentry.budget.available']._read_group(
            domain=domain,
            fields=['amount_subtotal:sum'],
            groupby=['budget_type'],
        )
        mapped_available = {x['budget_type']: x['amount_subtotal'] for x in rg_available}

        # 2. Reserved & distributed expense
        fields = ['amount_reserved', 'amount_reserved_valued', 'amount_expense', 'amount_expense_valued']
        rg_expense = self.env['carpentry.budget.expense.distributed']._read_group(
            domain=domain,
            fields=[field + ':sum' for field in fields],
            groupby=['budget_type'],
        )
        mapped_data = {
            x['budget_type']: {field: x[field] for field in fields}
            for x in rg_expense
        }

        # 3. Format data per column
        budget_types_workforce = self.env['account.analytic.account']._get_budget_type_workforce()
        for column in self.filtered('budget_types'):
            budget_types = column.budget_types.split(',')
            is_hour = all([
                budget_type in budget_types_workforce
                for budget_type in budget_types
            ])
            valued = '' if is_hour else '_valued'

            res[column.id]['budget'] = {
                'unit': 'h' if is_hour else '€',
                'available': human_readable(sum([
                    mapped_available.get(x, 0.0) for x in budget_types
                ])),
                'reserved': human_readable(sum([
                    mapped_data.get(x, {}).get('amount_reserved' + valued, 0.0) for x in budget_types
                ])),
                'expense': human_readable(sum([
                    mapped_data.get(x, {}).get('amount_expense' + valued, 0.0) for x in budget_types
                ])),
            }

        return res
