# -*- coding: utf-8 -*-

import time
from odoo import models, fields, api, _, Command, exceptions
from collections import defaultdict

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
        if not self.mapped('budget_type'):
            return res
        
        mapped_milestone_data = defaultdict(list)
        analytics = self.env['account.analytic.account'].search([('is_project_budget', '=', True)])
        budget_types_descr = dict(analytics._fields['budget_type']._description_selection(self.env))

        # 1. Retrieve all `available` and `reserved` budget for this launch
        #    budget_dict: format like {('carpentry.group.launch', launch.id, budget_type): amount}
        launch = self.env['carpentry.group.launch'].browse(launch_id_)
        brut = analytics._get_available_budget_initial(launch, groupby_budget='budget_type', brut_or_valued='brut')
        reserved = analytics._get_sum_reserved_budget(launch, groupby_budget='budget_type')

        def __format(budget_dict, column):
            key = ('carpentry.group.launch', launch.id, column.budget_type)
            return human_readable(budget_dict.get(key, 0.0))

        # 2. Compute data per column
        for column in self:
            if not column.budget_type:
                continue

            column_analytics = analytics.filtered(lambda x: x.budget_type == column.budget_type)
            is_hour = set(column_analytics.mapped('budget_unit')) == {'h'}

            res[column.id]['budget'] = {
                'tooltip': '[{}] {}' . format(
                    budget_types_descr.get(column.budget_type),
                    ', ' . join(column_analytics.mapped('name'))
                ),
                'unit': 'h' if is_hour else '€',
                'available': __format(brut, column),
                'reserved': __format(reserved, column),
            }

        return res
