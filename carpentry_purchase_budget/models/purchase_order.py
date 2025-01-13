# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from collections import defaultdict
from odoo.tools import float_compare

class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['purchase.order', 'project.default.mixin', 'carpentry.group.affectation.mixin']
    _carpentry_affectation_quantity = True
    # record: launch
    # group: analytic
    # section: order

    #====== Fields ======#
    # -- affectation matrix --
    affectation_ids = fields.One2many(
        inverse_name='section_id',
        domain=[('section_res_model', '=', _name)],
        compute='_compute_affectation_ids',
        store=True,
        readonly=False
    )
    
    # -- ui/logic fields --
    budget_analytic_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        string='Budgets',
        compute='_compute_budget_analytic_ids',
        help='Budgets selected in analytic distribution of lines in "Products" page.',
    )
    budget_unique_analytic_id = fields.Many2one(
        # Update lines' analytic distribution at once (budgets)
        comodel_name='account.analytic.account',
        string='Unique Budget',
        compute='_compute_budget_analytic_ids',
        inverse='_inverse_budget_unique_analytic_id',
        domain="[('budget_project_ids', '=', project_id)]",
        help="Change this field to reserve budget on this single one."
             " To consume different budgets, modify the 'analytic distribution'"
             " per line in 'Products' page.",
    )
    warning_budget = fields.Boolean(
        compute='_compute_warning_budget'
    )

    #====== Affectation refresh ======#
    @api.depends('launch_ids', 'order_line', 'order_line.analytic_distribution')
    def _compute_affectation_ids(self):
        """ Refresh budget matrix and auto-reservation when:
            - (un)selecting launches
            - (un)selecting budget analytic in order lines
        """
        for purchase in self:
            vals_list = purchase._get_affectation_ids_vals_list(temp=False)

            if purchase._has_real_affectation_matrix_changed(vals_list):
                purchase.affectation_ids = purchase._get_affectation_ids(vals_list)
                purchase._auto_update_budget_distribution()
                purchase.readonly_affectation = True # some way to inform users the budget matrix was re-computed
    
    @api.depends('order_line', 'order_line.analytic_distribution')
    def _compute_budget_analytic_ids(self):
        """ Compute budget analytics shortcuts """
        for purchase in self:
            budgets = purchase.order_line.analytic_ids.filtered('is_project_budget')

            purchase.budget_analytic_ids = budgets
            purchase.budget_unique_analytic_id = len(budgets) == 1 and budgets
    
    #====== Affectation mixin methods ======#
    def _get_record_refs(self):
        """ [Affectation Refresh] 'Lines' are launches (of real affectation) """
        return self.launch_ids._origin
    
    def _get_group_refs(self):
        """ [Affectation Refresh] 'Columns' of Purchase Order affectation matrix are analytic account
            present in the project's budgets
        """
        return self.budget_analytic_ids._origin.filtered(lambda x: x.budget_project_ids in self.project_id)
    
    def _get_affect_vals(self, mapped_model_ids, record_ref, group_ref, affectation=False):
        """ [Affectation Refresh] Store PO id in `section_ref` """
        return super()._get_affect_vals(mapped_model_ids, record_ref, group_ref, affectation) | {
            'section_model_id': mapped_model_ids.get(self._name),
            'section_id': self._origin.id,
        }

    def _get_domain_affect(self):
        return [
            ('section_res_model', '=', 'purchase.order'),
            ('section_id', 'in', self.ids)
        ]

    def _raise_if_no_affectations(self):
        raise exceptions.UserError(_(
            'There is no possible budget reservation. Please verify'
            ' if the Purchase Order has lines with analytic distribution,'
            ' (in "Products" page) and ensure some launches are selected.'
        ))

    #====== Compute ======#
    @api.depends('amount_untaxed', 'affectation_ids')
    def _compute_warning_budget(self):
        prec = self.env['decimal.precision'].precision_get('Product Price')
        states = ['to approve', 'approved', 'purchase', 'done']
        for purchase in self:
            compare = float_compare(purchase.amount_untaxed, purchase.sum_quantity_affected, precision_digits=prec)
            purchase.warning_budget = purchase.state in states and compare != 0

    # --- budget_unique_analytic_id (shortcut to set line analytic at once on the budget) ---
    def _inverse_budget_unique_analytic_id(self):
        """ Modify all lines analytic at once """
        for purchase in self:
            replaced_ids = purchase.order_line.analytic_ids.filtered('is_project_budget')
            added_id = purchase.budget_unique_analytic_id
            # Don't do shortcut when `added_id` is empty *and* the order has multiple budgets
            if added_id or len(replaced_ids) == 1:
                purchase.order_line._replace_analytic(replaced_ids.ids, added_id.id)

    #===== Business logics =====#
    def _auto_update_budget_distribution(self):
        """ Distribute line price (expenses) into budget reservation,
             according to remaining budget
        """
        budget_distribution = self._get_auto_budget_distribution()
        for affectation in self.affectation_ids:
            key = (affectation.record_id, affectation.group_id) # launch_id, analytic_id
            affectation.quantity_affected = budget_distribution.get(key, 0.0)
    
    def _get_auto_budget_distribution(self):
        """ Calculate suggestion for budget reservation of an order, considering:
             - total price per budget analytic in the order lines
             - remaining budget of selected launches, per analytic
            Values can be used for `quantity_affected` field of affectations

            :return: Dict like: {
                (launch.id, analytic.id): average-weighted amount, i.e.:
                    expense * remaining budget / total budget (per launch)
            }
        """
        self.ensure_one() # (!) `remaining_budget` must be computed per order
        line_total_price = self._get_price_by_analytic()
        remaining_budget = self.launch_ids._get_remaining_budget(
            section=self._origin,
            analytic_ids=list(set(line_total_price.keys())),
        )

        # Sums launch total available budget per analytic
        mapped_analytic_budget = defaultdict(float)
        for (launch_id, analytic_id), budget in remaining_budget.items():
            mapped_analytic_budget[analytic_id] += budget

        # Calculate automatic budget reservation (avg-weight)
        budget_distribution = {}
        for (launch_id, analytic_id), budget_launch in remaining_budget.items():
            total_price = line_total_price.get(analytic_id)
            total_budget = mapped_analytic_budget.get(analytic_id)

            reservation = total_budget and total_price * budget_launch / total_budget
            key = (launch_id, analytic_id)
            budget_distribution[key] = min(reservation or 0.0, total_budget)
        return budget_distribution

    def _get_price_by_analytic(self):
        """ Group-sum `price_subtotal` of purchase order lines by analytic account
            :return: Dict like {analytic_id: charged amount}
        """
        self.ensure_one()
        mapped_price = defaultdict(float)
        for line in self.order_line:
            for analytic_id, percentage in line.analytic_distribution.items():
                amount = line.price_subtotal * percentage / 100
                mapped_price[int(analytic_id)] += amount
        return mapped_price
