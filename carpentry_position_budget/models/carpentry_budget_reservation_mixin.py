# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.tools import float_round, float_is_zero
from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression

from collections import defaultdict
from datetime import datetime
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
    _carpentry_budget_reservation = True
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
    )
    date_budget = fields.Date(
        compute='_compute_date_budget',
        string='Budget date',
        store=True,
    )
    # amount_remaining = fields.Monetary(
    #     string='Budget',
    #     compute='_compute_amount_remaining',
    # )
    amount_budgetable = fields.Monetary(
        string='Budgetable Amount',
        compute='_compute_amount_budgetable',
        help="Cost amount imputed on the project."
             " Gain = 'Amount of reserved budget' - this amount"
    )
    sum_quantity_affected = fields.Float(
        store=True, # to search on Budget Reservation amount
        string='Amount of reserved budget',
        help='Sum of budget reservation'
    )
    amount_gain = fields.Monetary(
        compute='_compute_amount_gain',
    )
    amount_loss = fields.Monetary(
        compute='_compute_amount_gain',
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
        records.readonly_affectation = False
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
        return self._get_domain_affect('section')
    
    #====== Affectation refresh ======#
    def _get_domain_write_or_create(self, vals):
        """ For budget affectation, also filter by section_id"""
        return super()._get_domain_write_or_create(vals) + [
            ('section_id', '=', vals.get('section_id'))
        ]
    
    def _get_fields_affectation_refresh(self):
        return ['launch_ids', 'budget_analytic_ids']
    
    @api.onchange('launch_ids', 'budget_analytic_ids')
    def _set_readonly_affectation(self):
        """ Way to inform users the budget matrix must be re-computed """
        self.readonly_affectation = True
    
    def _get_mapped_records_per_groups(self, launchs, analytics):
        """ Filter which lines of budget reservation so we display only
            *launch & budget* launch with available budget (initially)
            => a.k.a. don't display a budget next to a launch if this launch never
                had this budget
            :return: {analytic.id: launchs}
        """
        if not launchs or not analytics:
            return {}
        
        model = 'carpentry.group.launch'
        self.env['carpentry.group.affectation'].flush_model(['group_id'])
        self._cr.execute(f"""
            SELECT
                budget.analytic_account_id,
                ARRAY_AGG(DISTINCT affectation.group_id) AS launch_ids
            FROM
                carpentry_group_affectation AS affectation
            INNER JOIN
                carpentry_position_budget AS budget
                ON budget.position_id = affectation.position_id
            WHERE
                affectation.group_id IN %(launchs)s AND
                affectation.group_model_id = (SELECT id FROM ir_model WHERE model = '{model}')
            GROUP BY budget.analytic_account_id
        """, {
            'launchs': tuple(launchs.ids),
        })
        return {row[0]: launchs.browse(row[1]) for row in self._cr.fetchall()}
    
    def _get_affectation_ids_vals_list(self, temp, record_refs=None, group_refs=None):
        """ Appends *Global Budget* (on the *project*) to the matrix """
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
            - (un)selecting budget analytic in section lines
        """
        for section in self:
            vals_list = section._get_affectation_ids_vals_list(temp=False)

            if section._has_real_affectation_matrix_changed(vals_list):
                section.affectation_ids = section._get_affectation_ids(vals_list) # create empty matrix
                section._auto_update_budget_distribution() # fills in

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

    def _get_domain_affect(self, group='section', group2_ids=None, group2='group'):
        """ Default `group` is `section` for budget reservation
            Needed for `_write_or_create_affectations`
        """
        return super()._get_domain_affect(group, group2_ids, group2)

    @api.depends('create_date')
    def _compute_date_budget(self):
        """ [To overwritte]
            Date's field on which budget reports can be filtered (expense & project result)
        """
        for section in self:
            if not section.date_budget:
                section.date_budget = section.create_date
            section.affectation_ids.date = section.date_budget

    #===== Compute amounts =====#
    @api.depends('affectation_ids', 'affectation_ids.quantity_affected')
    def _compute_sum_quantity_affected(self):
        """ [Overwritte]
            - Real-time computing => no read_group
            - (h) to (€) conversion if needed (PO and picking)
        """
        if self._is_quantity_affected_valued():
            for record in self:
                record.sum_quantity_affected = sum([
                    affectation.group_ref._value_amount(
                        affectation.quantity_affected,
                        record.project_id.date_start,
                        record.project_id.date,
                    )
                    for affectation in record.affectation_ids
                ])
        else:
            for record in self:
                record.sum_quantity_affected = sum(record.affectation_ids.mapped('quantity_affected'))

    def _is_quantity_affected_valued(self):
        return False

    def _compute_amount_budgetable(self):
        """ To be inherited """
        return

    @api.depends('affectation_ids')
    def _compute_amount_gain(self):
        prec = self.env['decimal.precision'].precision_get('Product Price')
        for section in self:
            not_canceled = not hasattr(section, 'state') or section.state != 'cancel'
            gain = float_round(section.sum_quantity_affected - section.amount_budgetable, precision_digits=prec)
            section.amount_gain = not_canceled and gain
            section.amount_loss = -1 * section.amount_gain

    #====== Compute/Inverse ======#
    @api.depends('project_id')
    def _compute_budget_analytic_ids(self):
        """ To be inherited """
        self._set_readonly_affectation()
        # self._compute_amount_remaining()

    #===== Business logics =====#
    def _auto_update_budget_distribution(self):
        """ Distribute line price (expenses) into budget reservation,
             according to remaining budget((, and clean affectation
             without remaining budget))
        """
        budget_distribution = self._get_auto_launch_budget_distribution()
        for affectation in self.affectation_ids:
            key = (affectation.record_res_model, affectation.record_id, affectation.group_id) # model, launch_id, analytic_id
            auto_reservation = budget_distribution.get(key, None)
            if auto_reservation != None:
                remaining = affectation.quantity_remaining_to_affect + affectation.quantity_affected
                affectation.quantity_affected = math.floor(
                    min(auto_reservation, remaining) * 100
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
        for (model, _, analytic_id), budget in remaining_budget.items():
            if model == 'carpentry.group.launch':
                mapped_launch_budget[analytic_id] += budget
        
        # Calculate automatic budget reservation (avg-weight)
        budget_distribution = {}
        for key, budget in remaining_budget.items():
            model, _, analytic_id = key
            total_price = total_by_analytic.get(analytic_id, 0.0)

            if model == 'carpentry.group.launch':
                launch_budget = mapped_launch_budget.get(analytic_id)
                auto_reservation = launch_budget and total_price * budget / launch_budget
            else: # project
                auto_reservation = total_price
            
            budget_distribution[key] = auto_reservation or 0.0
            # budget_distribution[key] = min(auto_reservation or 0.0, budget) # moved to previous method
        return budget_distribution

    def _get_mapped_project_analytics(self, domain_arg=[]):
        domain = [('project_id', 'in', self.project_id.ids)]
        if domain_arg:
            domain = expression.AND([domain, domain_arg])
        
        """ Get available budgets, per project """
        rg_result = self.env['account.move.budget.line'].read_group(
            domain=domain,
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
        return {}
        # to be inherited

    #===== Button =====#
    def action_open_budget(self, xml_id, context={}):
        """ From the document (PO, MO, picking)
            open *Available budget* or *Remaining budget* pivot view
            filtered on launches
        """
        action = self.env['ir.actions.act_window']._for_xml_id('carpentry_position_budget.' + xml_id)

        budget_types = self._get_budget_types()
        action['context'] = context | safe_eval(action['context'] or '{}') | {
            f'search_default_filter_{budget_type}': 1
            for budget_type in budget_types
        }
        action['domain'] = [
            ('group_res_model', 'in', ['project.project', 'carpentry.group.launch']),
            ('project_id', '=', self.project_id.id),
            ('launch_id', 'in', [False] + self.launch_ids._origin.ids),
        ]
        return action
    
    def open_launch_budget(self):
        return self.action_open_budget(
            xml_id='action_open_launch_budget',
            context={'search_default_filter_groupby_launch': 1}
        )
    
    def open_remaining_budget(self):
        return self.action_open_budget('action_open_budget_report_remaining')
