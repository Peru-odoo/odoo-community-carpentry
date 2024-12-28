# -*- coding: utf-8 -*-

from odoo import models, fields

# This adds budget fields & computation to Phases & Launches

class CarpentryGroupLaunch(models.Model):
    _name = 'carpentry.group.launch'
    _inherit = ['carpentry.group.launch', 'carpentry.group.budget.mixin']

    def _get_remaining_budget(self, section, mode='brut', analytic_ids=[]):
        """ Calculate [Initial Budget] - [Reservation], per launch & analytic
            :arg section: PO or MO record
            :option mode: 'brut' or 'valued'
            :option analytic_ids: (perf optim) if given, only those are searched in budget domain
                this is important because hour budget are valued if found, which
                might not be necessary (e.g. for purchases)
            :return: Dict like: 
                {(launch.id, analytic.id): remaining available budget}
        """
        brut, valued = self._get_available_budget_initial(analytic_ids)
        budget = brut if mode == 'brut' else valued
        reserved = self._get_sum_reserved_budget(section, analytic_ids, sign=-1)

        # careful: browse all keys and all rows of both `budget` and `reserved`
        # since they might be budget without reservation, or even reservation without budget
        remaining = reserved.copy() # are values are negative (`sign=-1`)
        for launch_id, budgets in budget.items():
            for analytic_id, amount in budgets.items():
                key = (launch_id, analytic_id)
                remaining[key] = remaining.get(key, 0.0) + amount
        return remaining
    
    def _get_available_budget_initial(self, analytic_ids=[]):
        """ :return: (brut, valued) where each item is a dict-of-dict like:
            {
                launch.id: {analytic.id: amount, ...},
                ...
            }
        """
        domain_budget = [('analytic_account_id', 'in', analytic_ids)] if analytic_ids else []
        brut, valued = self.env['carpentry.position.budget'].sudo().sum(
            quantities=self._get_quantities(),
            groupby_group=['group_id'],
            groupby_budget='analytic_account_id',
            domain_budget=domain_budget
        )
        return brut, valued
    
    def _get_sum_reserved_budget(self, section=None, analytic_ids=[], sign=1):
        """ Sum all budget reservation on launches and return it by launches & analytics
            :option section:     optional `section_ref` record (PO or MO) to be excluded from
                                  the sum. Useful to compute *remaining budgets* on POs and MOs
            :option analytc_ids: perf optim
            :option sign:        give `-1` so values are negative

            :return: Dict like:
                {(launch.id, analytic.id): sum of budget reservation}

            Note: budget reservation are *affectation* with `record_ref` being `launch_id`, and:
             - `group_id`: analytic account
             - `section_id`: the document reserving the budget (e.g. PO or MO)
             - `quantity_affected`: the reserved budget
            
        """
        domain = self._get_domain_affect(group='record')
        if section:
            section.ensure_one()
            domain += [
                ('section_res_model', '=', section._name),
                ('section_id', '!=', section.id),
            ]
        if analytic_ids:
            domain += [
                ('group_res_model', '=', 'account.analytic.account'),
                ('group_id', 'in', analytic_ids)
            ]
        
        rg_result = self.env['carpentry.group.affectation'].read_group(
            domain=domain,
            groupby=['record_id', 'group_id'],
            fields=['quantity_affected:sum']
        )
        return {
            (x['record_id'], x['group_id']): x['quantity_affected'] * sign
            for x in rg_result
        }
