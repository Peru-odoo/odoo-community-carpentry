# -*- coding: utf-8 -*-

from odoo import api, models, exceptions, _
from odoo.tools import float_is_zero, float_compare

class CarpentryAffectation(models.Model):
    _inherit = ["carpentry.affectation"]

    #===== CRUD =====#
    def write(self, vals):
        """ Prevent lowering `quantity_affected` of a
            position to launch (through a phase)
            if it causes negative budgets
        """
        res = super().write(vals)
        if any(x in vals for x in ('quantity_affected', 'affected')):
            launchs = self._get_launchs_and_children_launchs()
            self._clean_reservation_and_constrain_budget(launchs.ids)
        return res
    
    def unlink(self):
        """ Prevent deleting an affectation if it results
            a negative *remaining budget* on a PO, MO, ...
            :arg self: launch affectations
        """
        launchs = self._get_launchs_and_children_launchs()
        res = super().unlink()
        self._clean_reservation_and_constrain_budget(launchs.ids)
        return res
    
    @api.ondelete(at_uninstall=False)
    def _get_launchs_and_children_launchs(self):
        affectations_phase, affectations_launch = self._split()
        if affectations_phase:
            affectations_launch += affectations_phase.children_ids
        return affectations_launch.launch_id

    #===== Logics =====#
    def _clean_reservation_and_constrain_budget(self, launch_ids=[False], project_ids=[]):
        """ 1. Clean *empty* budget reservation already created
               but not possible anymore (no available budget)
            
            2. Prevents deleting the records (affectations or budget line)
               if it results a negative *remaining budget* on a PO, MO, ...
        """
        if (not launch_ids or launch_ids == [False]) and not project_ids: # optim
            return
        
        domain = [('launch_id', 'in', launch_ids)]
        if project_ids:
            domain += [('project_id', 'in', project_ids)]

        # 1. reservations not possible with no budget reservation => just clean them with no noise
        prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        reservations = self.env['carpentry.budget.reservation'].search(domain)
        reservations.filtered(
            lambda x: (
                float_is_zero(x.amount_initially_available, precision_digits=prec)
                and float_is_zero(x.amount_reserved, precision_digits=prec)
            )
        ).unlink()

        # 2.
        Remaining = self.env['carpentry.budget.remaining']
        self.env.flush_all() # required before view requests
        Remaining.invalidate_model()

        rg_result = Remaining._read_group(
            domain=domain,
            groupby=['project_id', 'launch_id', 'analytic_account_id'],
            fields=['amount_subtotal:sum', 'remaining_ids:array_agg(id)'],
            lazy=False,
        )
        remaining_ids = []
        for x in rg_result:
            if float_compare(x['amount_subtotal'], 0.0, precision_digits=prec) == -1:
                remaining_ids += x['remaining_ids']
        
        debug = True
        if debug:
            fields = ['project_id', 'launch_id', 'analytic_account_id', 'amount_subtotal',]
            print('domain', domain)
            print('negative_remainings', Remaining.browse(remaining_ids).read(fields))
        
        if bool(remaining_ids):
            kwargs = Remaining.browse(remaining_ids)._get_raise_to_reservations(_(
                "This action is not possible, elsewhise "
                "a budget reservation would be missing available budgets.",
            ))
            raise exceptions.RedirectWarning(**kwargs)
