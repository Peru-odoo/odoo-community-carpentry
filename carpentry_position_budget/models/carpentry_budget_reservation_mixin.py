# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from collections import defaultdict
import calendar

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
        compute='_compute_affectation_ids',
        store=True,
        readonly=False
    )
    budget_analytic_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        string='Budgets',
        compute='_compute_budget_analytic_ids',
        inverse='_inverse_budget_analytic_ids',
        domain="[('budget_project_ids', '=', project_id)]"
    )

    #===== CRUD =====#
    @api.model_create_multi
    def create(self, vals_list):
        """ When modifying some fields, we lock the affectation table.
            The matrix is unlocked at form save.
        """
        vals_list = [vals | {'readonly_affectation': False} for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        vals['readonly_affectation'] = False
        return super().write(vals)
    
    #====== Affectation refresh ======#
    def _get_affectation_ids_vals_list(self, temp, record_refs=None, group_refs=None):
        """ Appends *Global Cost* (on the *project*) to the matrix """
        _super = super()._get_affectation_ids_vals_list
        global_lines = self.project_id.budget_line_ids.filtered(lambda x: not x.is_computed_carpentry)
        global_budgets = self.budget_analytic_ids & global_lines.analytic_account_id
        
        vals_list = _super(temp)
        if self.project_id and global_budgets:
            vals_list += _super(temp, self.project_id, global_budgets)
        return vals_list

    @api.depends('launch_ids') # add `order_line` and `move_raw_ids` in PO/MO
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
                order.readonly_affectation = True # some way to inform users the budget matrix was re-computed

    #====== Affectation mixin methods ======#
    def _get_record_refs(self):
        """ [Affectation Refresh] 'Lines' are launches (of real affectation) """
        return self.launch_ids._origin
    
    def _get_group_refs(self):
        """ [Affectation Refresh] 'Columns' of PO/MO affectation matrix are project's *auto* budgets (yet)
             *auto* budgets are the ones computed from Launches logics
             `_get_affectation_ids_vals_list` appens project's global budgets to the matrix
        """
        launch_lines = self.project_id.budget_line_ids.filtered('is_computed_carpentry')
        return self.budget_analytic_ids & launch_lines.analytic_account_id

    def _get_affect_vals(self, mapped_model_ids, record_ref, group_ref, affectation=False):
        """ [Affectation Refresh] Store MO/PO id in `section_ref` """
        return super()._get_affect_vals(mapped_model_ids, record_ref, group_ref, affectation) | {
            'section_model_id': mapped_model_ids.get(self._name),
            'section_id': self._origin.id,
            'seq_section': calendar.timegm(self._origin.create_date.timetuple()),
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
    

    #====== Compute/Inverse ======#
    def _inverse_budget_analytic_ids(self):
        """ Manual budget choice => update line's analytic distribution """
        for purchase in self:
            replaced_ids = purchase.order_line.analytic_ids.filtered('is_project_budget')._origin
            project_budgets = purchase.project_id.budget_line_ids.analytic_account_id
            new_budgets = purchase.budget_analytic_ids & project_budgets # in the PO lines and the project

            nb_budgets = len(new_budgets)
            new_distrib = {x.id: 100/nb_budgets for x in new_budgets}
            
            purchase.order_line._replace_analytic(replaced_ids.ids, new_distrib)

    @api.onchange('budget_analytic_ids')
    def _set_readonly_affectation(self):
        self.readonly_affectation = True

    #===== Business logics =====#
    def _auto_update_budget_distribution(self):
        """ Distribute line price (expenses) into budget reservation,
             according to remaining budget
        """
        budget_distribution = self._get_auto_launch_budget_distribution()
        for affectation in self.affectation_ids:
            key = (affectation.record_res_model, affectation.record_id, affectation.group_id) # model, launch_id, analytic_id
            affectation.quantity_affected = budget_distribution.get(key, 0.0)
    
    def _get_auto_launch_budget_distribution(self):
        """ Calculate suggestion for budget reservation of an PO/MO, considering:
             - total price per budget analytic (in the order_line, move_raw_ids or workcenter),
                for budgets available in the PO/MO's project
             - remaining budget of selected launches, per analytic
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
            total_price = total_by_analytic.get(analytic_id)

            if model == 'carpentry.group.launch':
                launch_budget = mapped_launch_budget.get(analytic_id)
                auto_reservation = launch_budget and total_price * budget / launch_budget
            else: # project
                auto_reservation = budget
            
            max_reservation = remaining_budget.get(key, 0.0)
            budget_distribution[key] = min(auto_reservation or 0.0, max_reservation)
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
