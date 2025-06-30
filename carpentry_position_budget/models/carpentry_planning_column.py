# -*- coding: utf-8 -*-

from odoo import models, fields

def human_readable(num, scale=1000.0):
    return round(num) if num else 0.0
    for unit in ("", "k", "m"):
        if abs(num) < scale:
            return f"{num:3.0f}{unit}"
        num /= scale
    return f"{num:.0f}M"

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
        
        budget_types = []
        for budget_types_char in self.mapped('budget_types'):
            if not budget_types_char:
                continue

            for x in budget_types_char.split(','):
                if not x in budget_types:
                    budget_types.append(x)
    
        if not budget_types:
            return res
        
        analytics = self.env['account.analytic.account'].search([('is_project_budget', '=', True)])
        domain = [('launch_id', '=', launch_id_), ('budget_type', 'in', budget_types)]

        # 1. Available (brut)
        rg_available = self.env['carpentry.budget.available']._read_group(
            domain=domain,
            fields=['subtotal:sum'],
            groupby=['budget_type'],
        )
        mapped_available = {x['budget_type']: x['subtotal'] for x in rg_available}

        # 2. Reserved & distributed expense
        rg_expense = self.env['carpentry.budget.expense.distributed']._read_group(
            domain=domain,
            fields=['quantity_affected:sum', 'expense_distributed:sum'],
            groupby=['budget_type'],
        )
        mapped_reserved, mapped_expense = {}, {}
        for x in rg_expense:
            mapped_reserved[x['budget_type']] = x['quantity_affected']
            mapped_expense [x['budget_type']] = x['expense_distributed']

        # 3. Format data per column
        for column in self:
            budget_types = column.budget_types.split(',')
            if not budget_types:
                continue

            column_analytics = analytics.filtered(lambda x: x.budget_type in budget_types)
            is_hour = set(column_analytics.mapped('budget_unit')) == {'h'}

            res[column.id]['budget'] = {
                'unit': 'h' if is_hour else '€',
                'available': human_readable(sum([mapped_available.get(x, 0.0) for x in budget_types])),
                'reserved': human_readable(sum([mapped_reserved.get(x, 0.0) for x in budget_types])),
                'expense': human_readable(sum([mapped_expense.get(x, 0.0) for x in budget_types])),
            }

        return res
