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
    analytic_id = fields.Many2one(
        # Update lines' analytic distribution at once (budgets)
        comodel_name='account.analytic.account',
        string='Modify Budget',
        compute='_compute_analytic_id',
        inverse='_inverse_analytic_id',
        help="Change this field to reserve budget on this single one."
             " To consume different budgets, modify the 'analytic distribution'"
             " per line in 'Products' page."
    )
    warning_budget = fields.Boolean(
        compute='_compute_warning_budget'
    )

    # -- affectation matrix --
    affectation_ids = fields.One2many(
        readonly=False,
        inverse_name='section_id',
        domain=[('section_res_model', '=', _name)]
    )
    launch_ids = fields.One2many(
        comodel_name='carpentry.group.launch',
        string='Launches',
        compute='_compute_launch_ids',
        domain="[('project_id', '=', project_id)]"
    )
    
    #====== Affectation refresh ======#
    @api.depends('affectation_ids')
    def _compute_launch_ids(self):
        """ List `launch_ids` from existing affectations (many2many_checkboxes) """
        for purchase in self:
            purchase.launch_ids = purchase.affectation_ids.record_id or False
    
    @api.onchange('launch_ids')
    def _onchange_launch_ids(self):
        """ Refresh budget reservation/affectation matrix (tree) when (un)selecting launches """
        self.affectation_ids = self._get_affectation_ids()

    # (i) see also purchase_order_line.py > @api.onchange('analytic_distribution')
    # which refreshes purchase_order.affectation_ids
    
    #====== Affectation mixin methods ======#
    def _get_record_refs(self):
        """ [Affectation Refresh] 'Lines' are launches (of real affectation) """
        return self.launch_ids._origin
    
    def _get_group_refs(self):
        """ [Affectation Refresh] 'Columns' of Purchase Order affectation matrix are analytic account """
        return self.order_line.analytic_ids._origin
    
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

    #====== Compute ======#
    @api.depends('amount_untaxed', 'affectation_ids')
    def _compute_warning_budget(self):
        prec = self.env['decimal.precision'].precision_get('Product Price')
        states = ['to approve', 'approved', 'purchase', 'done']
        for purchase in self:
            compare = float_compare(purchase.amount_untaxed, purchase.sum_quantity_affected, precision_digits=prec)
            purchase.warning_budget = purchase.state in states and compare != 0
    
    # --- project_id (shortcut to set line analytic at once on the project) ---
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """ Modify all lines analytic at once """
        project_analytics = self.env.company.analytic_plan_id.account_ids.ids
        for purchase in self:
            purchase.order_line._replace_analytic(
                should_filter=lambda x: x in project_analytics,
                new=purchase.project_id.analytic_account_id.id
            )

    # --- analytic_id (shortcut to set line analytic at once on the budget) ---
    @api.depends('order_line', 'order_line.analytic_distribution')
    def _compute_analytic_id(self):
        """ Pre-set the field to the single-used analytic in lines, if any """
        for purchase in self:
            analytic_ids = purchase.order_line.analytic_ids.filtered('is_project_budget')
            purchase.analytic_id = len(analytic_ids) == 1 and analytic_ids.id
    
    @api.onchange('analytic_id')
    def _inverse_analytic_id(self):
        """ Modify all lines analytic at once """
        self.readonly_affectation = True # forces to refresh the matrix by user
        budget_analytics = self.order_line.analytic_ids.filtered('is_project_budget').ids
        for purchase in self:
            purchase.order_line._replace_analytic(
                should_filter=lambda x: x in budget_analytics,
                new=purchase.analytic_id.id
            )

    def commented():
        pass
        # @api.depends('order_line', 'order_line.analytic_distribution')
        # def _get_affectation_ids(self):
        #     """ 1. Add a row to the `x2m_2d_matrix`:
        #          When choosing 1 launch in `launch_ids` One2many
                
        #         2. Add column:
        #          When an analytic account is added/removed on a PO's line analytic
        #          distribution, add it to the budget-selection matrix (synchro)
        #     """
        #     for purchase in self:
        #         existing = set(purchase.affectation_ids.mapped('group_id'))
        #         selected = set(self.order_line.analytic_ids.filtered('is_project_budget').ids)

        #         to_add = selected - existing
        #         to_remove = existing - selected

        #         # 1. Unlink affectations of removed analytics
        #         purchase.affectation_ids.filtered(lambda x: x.group_id in to_remove).unlink()
        #         # 1. Add affectations of added analytics
        #         vals_list = [
        #             (
        #                 purchase._get_affect_vals(mapped_model_ids, record_ref=launch, group_ref=analytic)
        #                 | {'quantity_affected': mapped_quantity.get((launch.id, analytic.id))}
        #             )
        #             for launch in purchase.launch_ids
        #             for analytic in purchase.affectation_ids.group_ref
        #         ]
        #         purchase.affectation_ids = [Command.create(vals) for vals in vals_list]
        
        # def _inverse_launch_ids(self):
        #     self.ensure_one() # required for correct budget computation: 1 PO at a time
        #     mapped_model_ids = self._get_mapped_model_ids()
        #     mapped_quantity = self._get_budget_distribution()

        #     # 1. Unlink affectations of removed launches
        #     domain = [('record_id', 'not in', purchase.launch_ids)]
        #     purchase.affectation_ids.filtered_domain(domain).unlink()
            
        #     # 2. Add affectations of added launches
        #     vals_list = [
        #         (
        #             purchase._get_affect_vals(mapped_model_ids, record_ref=launch, group_ref=analytic)
        #             | {'quantity_affected': mapped_quantity.get((launch.id, analytic.id))}
        #         )
        #         for launch in purchase.launch_ids
        #         for analytic in purchase.affectation_ids.group_ref
        #     ]
        #     purchase.affectation_ids = [Command.create(vals) for vals in vals_list]

    #===== Business logics =====#
    def _auto_update_budget_distribution(self):
        """ Distribute line price (expenses) into budget reservation,
             according to remaining budget
        """
        budget_distribution = self._get_budget_distribution()
        for affectation in self.affectation_ids:
            key = (affectation.record_id, affectation.group_id) # launch_id, analytic_id
            affectation.quantity_affected = budget_distribution.get(key)
    
    def _get_budget_distribution(self):
        """ Calculate suggestion for budget reservation of an order, considering:
             - total price per budget analytic in the order lines
             - remaining budget of selected launches, per analytic
            Values can be used for `quantity_affected` field of affectations

            :return: Dict like: {
                (launch.id, analytic.id): average-weighted amount, i.e.:
                    expense * remaining budget / total budget (per launch)
            }
        """
        # (!) `remaining_budget` must be computed per order
        self.ensure_one()
        line_total_price = self._get_price_by_analytic()
        remaining_budget = self.launch_ids._get_remaining_budget(
            analytic_ids=set(line_total_price.keys())
        )

        # Sums launch total available budget per analytic
        mapped_analytic_budget = defaultdict(float)
        for (launch_id, analytic_id), budget in remaining_budget.items():
            mapped_analytic_budget[analytic_id] += budget

        # Calculate suggestion for remaining budget per launch & analytic (avg-weight)
        mapped_reservation = {}
        for (launch_id, analytic_id), budget in remaining_budget.items():
            total_price = line_total_price.get(analytic_id)
            total_budget = mapped_analytic_budget.get(analytic_id)

            # avg-weight
            reservation = total_budget and total_price * budget / total_budget
            key = (launch_id, analytic_id)
            mapped_reservation[key] = reservation
        return mapped_reservation

    def _get_price_by_analytic(self):
        """ Group-sum `price_subtotal` of purchase order lines by analytic account
            :return: Dict like {analytic_id: charged amount}
        """
        self.ensure_one()
        mapped_price = defaultdict(float)
        for line in self.order_line:
            for analytic_id, percentage in line.analytic_distribution.items():
                amount = line.price_subtotal * percentage
                mapped_price[analytic_id] += amount
        return mapped_price

    #===== Button =====#
    def button_automatic_distribution(self):
        self._auto_update_budget_distribution()
