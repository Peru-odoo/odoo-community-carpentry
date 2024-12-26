# -*- coding: utf-8 -*-

from odoo import models, fields

# This adds budget fields & computation to Phases & Launches

class CarpentryGroupLaunch(models.Model):
    _name = 'carpentry.group.launch'
    _inherit = ['carpentry.group.launch', 'carpentry.group.budget.mixin']

    def _get_remaining_budget(self, mode='brut', analytic_ids=[]):
        """ Calculate [Initial Budget] - [Reservation], per launch & analytic
            :analytic_ids: (perf optim) if given, only those are searched in budget domain
                this is important because hour budget are valued if found, which
                might not be necessary (e.g. for purchases)
            :return: Dict like: 
                {(launch.id, analytic.id): remaining available budget}
        """
        brut, valued = self._get_available_budget_initial(analytic_ids)
        budget = brut if mode == 'brut' else valued
        reserved = self._get_sum_reserved_budget()

        return {
            (launch_id, analytic_id):
            budget.get(launch_id, {}).get(analytic_id, 0.0) - reservation
            for (launch_id, analytic_id), reservation in reserved.items()
        }
    
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
    
    def _get_sum_reserved_budget(self, analytic_ids):
        """ Fetch budget reservation of launches and return them summed by analytic
             note: when `launch_id` is in `record_ref`, it's a budget reservation and:
             - `group_id` is analytic account
             - `section_id` is the document (e.g. purchase order)
             - `quantity_affected` is a budget
            
            :return: Dict like:
                {(launch.id, analytic.id): sum of budget reservation}
        """
        domain = self._get_domain_affect(group='record') + [
            ('group_res_model', '=', 'account.analytic.account'),
            ('group_id', 'in', analytic_ids),
        ]
        rg_result = self.env['carpentry.group.affectation'].read_group(
            domain=domain,
            groupby=['record_id', 'group_id'],
            fields=['quantity_affected:sum']
        )
        return {
            (x['record_id'][0], x['group_id'][0]): x['quantity_affected']
            for x in rg_result
        }
