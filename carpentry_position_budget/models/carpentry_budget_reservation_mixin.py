# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval

from collections import defaultdict
from datetime import datetime
from odoo.tools import float_round
import calendar
import math

class CarpentryBudgetReservationMixin(models.AbstractModel):
    """ Budget reservation from Affectations
        Relevant for Purchase Orders, Manufacturing Orders and Pickings
    """
    _name = 'carpentry.budget.reservation.mixin'
    _inherit = ['carpentry.group.affectation.mixin']
    _description = 'Carpentry Budget Reservation Mixin'
    _carpentry_affectation_quantity = True
    # record: `launch` or `project`
    # group: analytic
    # section: order

    affectation_ids = fields.One2many(
        inverse_name='section_id',
    )
    readonly_affectation = fields.Boolean(
        default=False
    )
    budget_analytic_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        string='Budgets',
        compute='_compute_budget_analytic_ids',
        inverse='_inverse_budget_analytic_ids',
    )
    amount_budgetable = fields.Monetary(
        string='Budgetable Amount',
        compute='_compute_amount_budgetable',
        help="Cost amount imputed on the project."
             " Gain = 'Amount of reserved budget' - this amount"
    )
    sum_quantity_affected = fields.Float(
        store=True, # to search on Budget Reservation amount on Purchase Orders
        string='Amount of reserved budget',
        help='Sum of budget reservation'
    )
    amount_gain = fields.Monetary(
        compute='_compute_amount_gain'
    )
    amount_loss = fields.Monetary(
        compute='_compute_amount_gain'
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
    )

    #===== CRUD =====#
    @api.model_create_multi
    def create(self, vals_list):
        """ When modifying some fields, we lock the affectation table.
            The matrix is unlocked at form save.
        """
        records = super().create(vals_list)
        records._compute_affectation_ids()
        return records

    def write(self, vals):
        vals['readonly_affectation'] = False
        res = super().write(vals)
        fields = self._get_fields_affectation_refresh()
        if any(field in vals for field in fields):
            self._compute_affectation_ids()
        return res
    
    def _get_unlink_domain(self):
        """ When deleting a PO/MO/picking,
            delete the related the affectation
        """
        return expression.OR([
            super()._get_unlink_domain(),
            self._get_domain_affect('section'),
        ])
    
    #====== Affectation refresh ======#
    def _get_fields_affectation_refresh(self):
        return ['launch_ids', 'budget_analytic_ids']
    
    @api.onchange('launch_ids', 'budget_analytic_ids')
    def _set_readonly_affectation(self):
        """ Way to inform users the budget matrix must be re-computed """
        self.sudo().readonly_affectation = True
    
    def _get_affectation_ids_vals_list(self, temp, record_refs=None, group_refs=None):
        """ Appends *Global Cost* (on the *project*) to the matrix """
        _super = super()._get_affectation_ids_vals_list
        global_lines = self.project_id._origin.budget_line_ids.filtered(lambda x: not x.is_computed_carpentry)
        global_budgets = self.budget_analytic_ids._origin & global_lines.analytic_account_id
        
        vals_list = _super(temp)
        if self.project_id and global_budgets:
            vals_list += _super(temp, self.project_id, global_budgets)
        return vals_list

    def _compute_affectation_ids(self):
        """ Refresh budget matrix and auto-reservation when:
            - (un)selecting launches
            - (un)selecting budget analytic in order lines
        """
        for order in self:
            vals_list = order._get_affectation_ids_vals_list(temp=False)

            if order._has_real_affectation_matrix_changed(vals_list):
                order.affectation_ids = order._get_affectation_ids(vals_list) # create empty matrix
                order._auto_update_budget_distribution() # fills in

    #====== Affectation mixin methods ======#
    def _get_record_refs(self):
        """ [Affectation Refresh] 'Lines' are launches (of real affectation) """
        return self.launch_ids._origin
    
    def _get_group_refs(self):
        """ [Affectation Refresh] 'Columns' of PO/MO affectation matrix are project's *computed* budgets (yet)
             *computed* budgets are the ones computed from Launches logics
            (!!!) `_get_affectation_ids_vals_list` appends project's global budgets to the matrix
        """
        computed_lines = self.project_id._origin.budget_line_ids.filtered('is_computed_carpentry')
        return self.budget_analytic_ids._origin & computed_lines.analytic_account_id

    def _get_affect_vals(self, mapped_model_ids, record_ref, group_ref, affectation=False):
        """ [Affectation Refresh] Store MO/PO id in `section_ref` """
        date_seq = self._origin.create_date if self.id else datetime.now()
        
        return super()._get_affect_vals(mapped_model_ids, record_ref, group_ref, affectation) | {
            'section_model_id': mapped_model_ids.get(self._name),
            'section_id': self._origin.id,
            'seq_section': calendar.timegm(date_seq.timetuple()),
        }

    def _get_domain_affect(self):
        return [
            ('section_res_model', '=', self._name),
            ('section_id', 'in', self.ids)
        ]

    def _raise_if_no_affectations(self):
        raise exceptions.UserError(_(
            'There is no possible budget reservation. Please ensure:\n'
            ' - launches are selected;\n'
            ' - the project has budget on the selected analytic accounts;\n'
            ' - for Purchase Orders, that lines have analytic distribution,'
            ' (in "Products" page).'
        ))
    
    #===== Compute amounts =====#
    @api.depends('affectation_ids.quantity_affected')
    def _compute_sum_quantity_affected(self):
        """ [Overwritte] PO needs real-time computing => no read_group """
        for record in self:
            record.sum_quantity_affected = sum(record.affectation_ids.mapped('quantity_affected'))
    
    def _compute_amount_budgetable(self):
        """ To be inherited """
        return

    @api.depends('affectation_ids')
    def _compute_amount_gain(self):
        prec = self.env['decimal.precision'].precision_get('Product Price')
        for purchase in self:
            gain = float_round(purchase.sum_quantity_affected - purchase.amount_budgetable, precision_digits=prec)
            purchase.amount_gain = purchase.state != 'cancel' and gain
            purchase.amount_loss = -1 * purchase.amount_gain

    #====== Compute/Inverse ======#
    def _inverse_budget_analytic_ids(self):
        """ Manual budget choice => update line's analytic distribution """
        for purchase in self:
            replaced_ids = purchase.order_line.analytic_ids._origin.filtered('is_project_budget')
            project_budgets = purchase.project_id._origin.budget_line_ids.analytic_account_id
            new_budgets = purchase.budget_analytic_ids & project_budgets # in the PO lines and the project

            nb_budgets = len(new_budgets)
            new_distrib = {x.id: 100/nb_budgets for x in new_budgets}
            
            purchase.order_line._replace_analytic(replaced_ids.ids, new_distrib, 'budget')

    #===== Business logics =====#
    def _auto_update_budget_distribution(self):
        """ Distribute line price (expenses) into budget reservation,
             according to remaining budget
        """
        budget_distribution = self._get_auto_launch_budget_distribution()
        for affectation in self.affectation_ids:
            key = (affectation.record_res_model, affectation.record_id, affectation.group_id) # model, launch_id, analytic_id
            auto_reservation = budget_distribution.get(key, None)
            if auto_reservation != None:
                affectation.quantity_affected = math.floor(
                    min(auto_reservation, affectation.quantity_remaining_to_affect) * 100
                ) / 100.0
    
    def _get_auto_launch_budget_distribution(self):
        """ Calculate suggestion for budget reservation of a PO or MO, considering:
             - total real cost, per budget analytic (e.g. in the order_line or stock moves),
                for budgets available in the PO/MO's project
             - maximized to the remaining budget of selected launches, per analytic
            Values can be used for `quantity_affected` field of affectations

            :return: Dict like: {
                ('launch' or 'project', launch-or-project.id, analytic.id): average-weighted amount, i.e.:
                    expense * remaining budget / total budget (per launch)
            }
        """
        self.ensure_one() # (!) `remaining_budget` must be computed per order
        total_by_analytic = self._get_total_by_analytic()
        analytics = self.env['account.analytic.account'].sudo().browse(set(total_by_analytic.keys()))
        remaining_budget = analytics._get_remaining_budget(self.launch_ids, self._origin)

        # Sums launch total available budget per analytic
        mapped_launch_budget = defaultdict(float)
        for (model, launch_id, analytic_id), budget in remaining_budget.items():
            if model == 'carpentry.group.launch':
                mapped_launch_budget[analytic_id] += budget
        
        # Calculate automatic budget reservation (avg-weight)
        budget_distribution = {}
        for key, budget in remaining_budget.items():
            model, record_id, analytic_id = key
            total_price = total_by_analytic.get(analytic_id, 0.0)

            if model == 'carpentry.group.launch':
                launch_budget = mapped_launch_budget.get(analytic_id)
                auto_reservation = launch_budget and total_price * budget / launch_budget
            else: # project
                auto_reservation = total_price
            
            budget_distribution[key] = auto_reservation or 0.0
            # budget_distribution[key] = min(auto_reservation or 0.0, budget) # moved to previous method
        return budget_distribution

    def _get_mapped_project_analytics(self):
        """ Get available budgets, per project """
        rg_result = self.env['account.move.budget.line'].read_group(
            domain=[('project_id', 'in', self.project_id.ids)],
            groupby=['project_id'],
            fields=['analytic_account_id:array_agg']
        )
        return {x['project_id'][0]: x['analytic_account_id'] for x in rg_result}

    def _get_total_by_analytic(self):
        """ :return: Dict like {analytic_id: real cost} where *real cost* is:
            - for PO: untaxed total of lines with *consumable* products only
            - for MO: addition of:
                > move_raw_ids values
                > workcenter hours
        """
        # to be inherited

    #===== Button =====#
    def open_remaining_budget(self):
        """ From the document (PO, MO, picking),
            open *Remaining budget* pivot view
        """
        action = self.env['ir.actions.act_window']._for_xml_id(
            'carpentry_position_budget.action_open_budget_report_remaining'
        )

        budget_types = self._get_budget_types()
        action['context'] = safe_eval(action['context'] or '{}') | {
            f'search_default_filter_{budget_type}': 1
            for budget_type in budget_types
        }
        action['domain'] = [
            ('project_id', '=', self.project_id.id),
            ('launch_id', 'in', [False] + self.launch_ids._origin.ids)
        ]
        return action
