# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from collections import defaultdict

class PurchaseOrderLine(models.Model):
    _inherit = ['purchase.order.line']
    
    project_id = fields.Many2one(
        related='order_id.project_id',
        store=True,
    )
    analytic_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        compute='_compute_analytic_ids',
        string='Analytic Accounts'
    )

    #====== Constrain ======#
    @api.constrains('analytic_distribution')
    def _constrain_analytic_project(self):
        """ Prevent defining different project analytic on PO line:
            - internal project for Storable product
            - PO's project for others
        """
        for line in self:
            project_plan = line.company_id.analytic_plan_id
            to_verify = line.analytic_ids.filtered(lambda x: x.plan_id == project_plan)
            if line.product_id.type == 'product':
                allowed = line.company_id.internal_project_id.analytic_account_id
            else:
                allowed = line.order_id.project_id.analytic_account_id

            if to_verify and allowed and to_verify != allowed:
                raise exceptions.ValidationError(_(
                    "The only allowed project in Analytic Distribution is the"
                    " purchase order's one (or the internal project for storable"
                    " products)."
                ))

    #====== Compute ======#
    @api.depends('analytic_distribution')
    def _compute_analytic_ids(self):
        """ Gather analytic account selected in the line's analytic distribution """
        for line in self:
            new_distrib = line.analytic_distribution
            line.analytic_ids = new_distrib and [Command.set([int(x) for x in new_distrib.keys()])]

    @api.depends('order_id.project_id')
    def _compute_analytic_distribution(self):
        """ Apply to line's analytic the purchase order's project analytic """
        res = super()._compute_analytic_distribution()
        self.order_id._onchange_project_id()
        return res
    
    #===== Business logics =====#
    def _replace_analytic(self, replaced_ids, new_distrib={}, analytic_plan=False):
        """ Called from Purchase Order
            :arg replaced_ids:      `analytic_ids` to be replaced (to delete) in line analytic distribution
            :arg added_id:          single replacement `analytic_id` in place of `replaced_ids`
            :option analytic_plan:  if set to 'project', forces *Internal* project analytic for storable products 
        """
        default_analytic = self._get_default_storable_analytic(analytic_plan)
        for line in self:
            if line.display_type:
                # line without products: do nothing
                continue
            
            # if we're replacing analytic from project, keep other analytics plan (e.g. budgets)
            kept = {} if not line.analytic_distribution else {
                k: v for k, v in line.analytic_distribution.items()
                if int(k) not in replaced_ids
            }

            # enforce default val for storable products (e.g. internal project)
            vals = new_distrib
            if line.product_id.type == 'product':
                vals = {default_analytic.id: 100} if default_analytic else {}
            line.analytic_distribution = kept | vals

    def _get_default_storable_analytic(self, analytic_plan):
        """ Inherited in `carpentry_purchase_budget` for default budget """
        if analytic_plan == 'project':
            return self.company_id.internal_project_id.analytic_account_id
