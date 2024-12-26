# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from collections import defaultdict

class PurchaseOrderLine(models.Model):
    _inherit = ['purchase.order.line']

    project_id = fields.Many2one(
        related='order_id.project_id'
    )
    analytic_ids = fields.One2many(
        comodel_name='account.analytic.account',
        compute='_compute_analytic_ids'
    )

    #====== Constrain ======#
    @api.depends('analytic_distribution')
    def _constrain_analytic_to_project(self):
        """ Prevent setting different project analytic than PO's project """
        project_analytics = self.env.company.analytic_plan_id.children_ids.ids
        for line in self:
            allowed = line.project_id.analytic_account_id.id
            if any(x in project_analytics and x != allowed):
                raise exceptions.ValidationError(_(
                    "The only allowed project in Analytic Distribution is the"
                    " one defined on this purchase order."
                ))

    @api.depends('analytic_distribution')
    def _constrain_analytic_to_project_budget(self):
        """ Prevent choosing an analytic account on a PO line only to the ones existing
            in the budget of the PO's project
            Indeed the Analytic popover makes all analytic accounts selectable
            but we wished having selectable only the ones in the project budget
        """
        # Get analytic account used in project's budget
        rg_result = self.env['account.move.budget.line'].sudo().read_group(
            domain=[('project_id', 'in', self.project_id.ids)],
            groupby=['project_id'],
            fields=['analytic_account_id:array_agg']
        )
        project_analytics = {x['project_id'][0]: x['analytic_account_id'] for x in rg_result}

        for line in self:
            to_verify = line.analytic_ids.filtered('is_project_budget')
            allowed = project_analytics.get(line.project_id.id)
            
            # let's verify if the budget of the PO's project actually foresee budget for those accounts
            if any(x not in allowed for x in to_verify.ids):
                raise exceptions.ValidationError(_(
                    'There is not budget on the project %(project)s for this'
                    ' (or one of these) analytic account(s): \n%(analytics)s',
                    project=line.project_id.display_name,
                    analytics=to_verify.mapped('name')
                ))

    #====== Compute ======#
    @api.depends('analytic_distribution')
    def _compute_analytic_ids(self):
        """ Gather analytic account selected in the line's analytic distribution
            and update budget matrix
        """
        for line in self:
            line.analytic_ids = line.analytic_distribution.keys()
        # refresh budget matrix
        self.order_id._compute_affectation_ids_temp()

    #===== Business logics =====#
    def _replace_line_analytic(self, should_replace, new):
        """ Called from Purchase Order
            Remove all analytic selection matching `should_replace`
            and set 1 analytic at 100% on `new`
            
            :arg self:           Recordset of PO lines
            :arg should_replace: Method accepting `analytic_id` as single arg
                                  and returning a boolean 
            :arg new:            New analytic to set
        """
        for line in self:
            line.analytic_distribution = {
                k: v for k, v in line.analytic_distribution.items()
                if not should_replace(k)
            } | {new: 100}
