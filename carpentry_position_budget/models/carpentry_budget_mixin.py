# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.tools import float_round, float_is_zero
from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression

from lxml import etree
from odoo.tools.misc import frozendict

from datetime import datetime
import calendar
from collections import defaultdict

class CarpentryBudgetMixin(models.AbstractModel):
    """ Budget reservation fields & methods for inheriting models (records*)
        to reserve budget in `carpentry.budget.reservation`
        (*) records are like: Purchase Orders, Manufacturing Orders, Pickings, Tasks and Budget Balances

        This mixin is the equivalent of `carpentry.affectation.mixin` for `carpentry.group.(phase|launch)`
    """
    _name = 'carpentry.budget.mixin'
    _description = 'Carpentry Budget Reservation Mixin'
    _record_field = '' # to inherit, like 'balance_id'
    _record_fields_expense = [] # to inherit, like 'order_line'

    _carpentry_budget_reservation = True # for action in Tree view of report `carpentry.budget.remaining`
    _carpentry_budget_alert_banner_xpath = "//div[hasclass('oe_title')]"
    _carpentry_budget_smartbuttons_xpath = '//div[@name="button_box"]/button[last()]'
    _carpentry_budget_notebook_page_xpath = '//page[@name="products"]'
    _carpentry_budget_sheet_name = 'Budget'
    _carpentry_budget_choice = True
    _carpentry_budget_last_valuation_step = False # whether temporary alert may be displayed

    #===== Fields =====#
    reservation_ids = fields.One2many(
        comodel_name='carpentry.budget.reservation',
        inverse_name='balance_id', # to overwitte
        string='Budget reservations',
        context={'active_test': False},
    )
    budget_analytic_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        string='Budgets',
        domain="[('budget_project_ids', '=', project_id)]",
        store=True,
    )
    expense_ids = fields.One2many(
        comodel_name='carpentry.budget.expense',
        inverse_name='balance_id', # to overwitte
        string='Expense',
        depends=['project_id'],
        context={'active_test': False},
    )
    other_expense_ids = fields.Many2many(
        comodel_name='carpentry.budget.expense',
        string='Other expenses',
        compute='_compute_other_expense_ids',
        context={'active_test': False},
    )
    date_budget = fields.Date(
        compute='_compute_date_budget',
        string='Budget date',
        store=True,
    )
    # amount
    total_budget_reserved = fields.Float(
        # brut *or* valued
        compute='_compute_budget_totals',
        string='Reserved budget',
        store=True,
    )
    total_budgetable = fields.Float(
        # brut *or* valued
        # amount shown in budget reservation alert
        # expense for PO, picking, components
        # planned hours for tasks & work orders
        compute='_compute_view_fields',
    )
    total_expense_valued = fields.Monetary(
        string="Real expense",
        compute='_compute_budget_totals',
        help="Total cost imputed to the budgets",
        store=True,
    )
    budget_unit = fields.Char(
        string='Budget unit',
        default='€',
        store=False,
    )
    amount_gain = fields.Monetary(compute='_compute_budget_totals',store=True,)
    amount_loss = fields.Monetary(compute='_compute_view_fields',)
    # -- view fields --
    readonly_reservation = fields.Boolean(
        compute='_compute_readonly_reservation',
    )
    readonly_budget_analytic_ids = fields.Boolean(
        compute='_compute_readonly_budget_analytic_ids',
    )
    can_reserve_budget = fields.Boolean(
        compute='_compute_can_reserve_budget',
        search='_search_can_reserve_budget',
    )
    show_gain = fields.Boolean(compute='_compute_view_fields',)
    is_temporary_gain = fields.Boolean(compute='_compute_view_fields',)
    text_no_reservation = fields.Char(compute='_compute_view_fields',)
    # currency
    project_id = fields.Many2one(comodel_name='project.project')
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=True,
        readonly=True,
        default=lambda self: self.env.company.currency_id.id
    )
    
    #===== CRUD : reservations populate & line's analytic_distribution =====#
    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)._refresh_reservations()

    def write(self, vals):
        res = super().write(vals)

        # -- after `write` --
        # update `budget_analytic_ids` (if needed) and `reservation_ids`
        budget_analytics = any([field in vals for field in self._depends_expense_temporary()])
        if budget_analytics or any([field in vals for field in ('launch_ids', 'budget_analytic_ids')]):
            self = self._refresh_reservations(budget_analytics)
        
        # cascade some record's fields to reservations
        fields = ('sequence', 'active', 'date_budget')
        if any(field in vals for field in fields):
            self.reservation_ids._update_record_fields()

        return res
    
    def _refresh_reservations(self, budget_analytics=False):
        """ Shortcut to other method to:
            - refresh `budget_analytic_ids`, if needed
            - populate+update `reservation_ids`
        """
        self = self.with_context(carpentry_no_compute_budget_totals=True) # perf optim
        rg_result = self._get_rg_result_expense() # perf: this call is very expensive

        if budget_analytics:
            self._populate_budget_analytics(rg_result)
        self._populate_budget_reservations(rg_result)

        return self # for create

    def _depends_expense_temporary(self):
        """ To inherite. Fields that triggers `_populate_budget_reservations`
            Example: ['order_line', 'order_line.analytic_distribution', 'amount_untaxed']
        """
        return []
    def _depends_expense_permanent(self):
        """ To inherite. @api.depends for `_compute_budget_totals`
            Inherites should add fields for *permanent* expenses @api.depends
        """
        return (
            # for total_budget_reserved and/or temp expense
            self._depends_expense_temporary() + ['reservation_ids.amount_reserved']
            # project changes
            + ([
                'project_id.date', 'project_id.date_start',
                'reservation_ids.analytic_account_id.timesheet_cost_history_ids.starting_date',
                'reservation_ids.analytic_account_id.timesheet_cost_history_ids.date_to',
                'reservation_ids.analytic_account_id.timesheet_cost_history_ids.hourly_cost',
            ] if self._should_value_budget_reservation() else [])
        )
    
    #====== Analytic mixin ======#
    @api.onchange('project_id')
    def _cascade_project_to_line_analytic_distrib(self, new_project_id=None):
        return super()._cascade_project_to_line_analytic_distrib(new_project_id)
    
    #===== Compute =====#
    def _compute_state(self):
        """ Ensure `reservation_ids.active` follows `record.state`,
            which mostly is a computed stored field and thus not catched in `write`
        """
        if hasattr(super(), '_compute_state'):
            res = super()._compute_state()
            self.reservation_ids._update_record_fields()
            return res
    
    @api.depends(lambda self: (
        ['project_id', 'launch_ids', 'budget_analytic_ids']
        + self._depends_expense_temporary()
    ))
    def _compute_readonly_reservation(self):
        """ Way to inform users the budget matrix must be re-computed
            1. At page load, self == self._origin
            2. At any fields changes, self == <NewId ...>
        """
        self.readonly_reservation = not bool(self == self._origin)

    @api.depends(lambda self: 
        ['project_id', 'launch_ids']
        + self._depends_expense_temporary()
    )
    def _compute_readonly_budget_analytic_ids(self):
        """ Same than `readonly_reservation`, but
             let `budget_analytic_ids` writable when
             modifying `budget_analytic_ids` itself
        """
        self.readonly_budget_analytic_ids = not bool(self == self._origin)

    #===== Compute =====#
    #--- View fields ---#
    def _depends_can_reserve_budget(self):
        return ['state']
    
    def _get_show_gain(self, is_gain_zero):
        self.ensure_one()
        return self.can_reserve_budget and not is_gain_zero

    def _get_domain_is_temporary_gain(self):
        """ Whether to show alert about *temporary gain/loss* estimation """
        return []
    
    @api.depends(lambda self: self._depends_can_reserve_budget())
    def _compute_can_reserve_budget(self):
        domain_budget = self._get_domain_can_reserve_budget()
        for record in self:
            record.can_reserve_budget = bool(record.filtered_domain(domain_budget))

    @api.model
    def _search_can_reserve_budget(self, operator, value):
        domain = self._get_domain_can_reserve_budget()
        if (
            operator not in expression.NEGATIVE_TERM_OPERATORS and value
            or operator in expression.NEGATIVE_TERM_OPERATORS and not value
        ):
            return domain
        else:
            return expression.distribute_not(['!'] + domain)

    def _get_domain_can_reserve_budget(self):
        """ Prevent budget reservation under some conditions """
        return [('state', '!=', 'cancel'),]
    
    def _depends_view_fields(self):
        return (
            ['reservation_ids', 'budget_analytic_ids', 'launch_ids',
             'total_expense_valued', 'amount_gain']
            + [part[0] for part in self._get_domain_is_temporary_gain()]
        )
    @api.depends(lambda self: self._depends_view_fields())
    def _compute_view_fields(self, field_suffix=''):
        """ After computation of totals, configures the UI layout of record' form
            This must stay simple logic quick to execute (called twice in MRP)
        """
        prec = self.env['decimal.precision'].precision_get('Product Price')

        for record in self:
            record._compute_view_fields_one(prec, field_suffix)
    
    def _compute_view_fields_one(self, prec, field_suffix):
        domain_temporary = self._get_domain_is_temporary_gain()
        is_temporary = bool(self.filtered_domain(domain_temporary))
        is_gain_zero = float_is_zero(self['amount_gain' + field_suffix], precision_digits=prec)
        affectations = self['reservation_ids' + field_suffix]

        self['amount_loss' + field_suffix] = -1 * self['amount_gain' + field_suffix]
        self['total_budgetable' + field_suffix] = self['total_expense_valued' + field_suffix]
        self['show_gain' + field_suffix] = self._get_show_gain(is_gain_zero)
        self['is_temporary_gain' + field_suffix] = is_temporary

        # text when no affectation due to launchs or budget centers
        text = ''
        if not affectations:
            budgets, launchs = self['budget_analytic_ids' + field_suffix], self['launch_ids']
            if budgets and launchs:
                text = _(
                    'There is no budget center with remaining budget. '
                    'Verify if selected budget center(s) do(es) exist in the project '
                    'and have budget.'
                )
            else:
                if not budgets and not launchs:
                    word = _('budget center(s) and possibly launch(s)')
                elif not budgets:
                    word = _('budget center(s)')
                else:
                    word = _('launch(s)')
                text = _('Please select %s in order to reserve budget.', word)
        self['text_no_reservation' + field_suffix] = text

    #--- Date, expense & amounts ---#
    @api.depends('create_date')
    def _compute_date_budget(self):
        """ [To overwritte]
            Date's field on which budget reports can be filtered (expense & project result)
        """
        print(' === _compute_date_budget ===')
        for record in self:
            if not record.date_budget:
                record.date_budget = record.create_date
            record.reservation_ids.date = record.date_budget
    
    @api.depends('project_id')
    def _compute_other_expense_ids(self):
        for record in self:
            record.other_expense_ids = record.expense_ids._origin.filtered(
                lambda x: x.analytic_account_id not in record.reservation_ids.analytic_account_id
            )

    def _should_value_budget_reservation(self):
        """ True on PO and picking: always in € """
        return False

    def _get_rg_result_expense(self):
        """ Return `rg_result` for `_compute_budget_totals` and `_get_total_budgetable_by_analytic` """
        debug = False
        if debug:
            print(' === _get_rg_result_expense (start) ===')
        
        # flush Record and its Lines
        self.flush_recordset()
        for field in self._record_fields_expense:
            self[field].flush_model()
        
        # read_group (-> this call is very expensive)
        Expense = self.env['carpentry.budget.expense'].with_context(active_test=False).sudo()
        rg_result = Expense.read_group(
            domain=[(self._record_field, 'in', self._origin.ids)],
            groupby=['analytic_account_id', self._record_field],
            fields=[
                'budget_type:array_agg',
                'amount_reserved:sum', 'amount_reserved_valued:sum',
                'amount_expense:sum', 'amount_expense_valued:sum',
                'amount_gain:sum',
            ],
            lazy=False,
        )

        if debug:
            print(' == _get_rg_result_expense (result) == ')
            print('expense_all', Expense.search_read(
                [(self._record_field, 'in', self[self._record_fields].ids)],
                ['analytic_account_id', 'active', self._record_field, 'amount_expense', 'amount_reserved']
            ))
            print('rg_result', rg_result)
        return rg_result

    @api.depends(lambda self: self._depends_expense_permanent())
    def _compute_budget_totals(self, groupby_analytic=False, rg_result=None):
        """ Call `carpentry.budget.expense` to compute:
            - total_budget_reserved
            - total_expense_valued
            - amount_gain

            :option groupby_analytic: for MRP
            :option `rg_result`: 
        """
        debug = True
        if debug:
            print(' === _compute_budget_totals (start) ===')

        # optim: don't call the heavy SQL on user action
        #        and wait for the form to be saved
        if (
            self._context.get('carpentry_no_compute_budget_totals')
            or isinstance(fields.first(self), models.NewId)
        ):
            return

        mapped_totals = defaultdict(dict) if groupby_analytic else {}
        pivot_analytic_to_budget_type = {}

        _valued = '_valued' if self._should_value_budget_reservation() else ''
        total_fields = ['amount_reserved' + _valued, 'amount_expense_valued', 'amount_gain']
        rg_result = rg_result or self._get_rg_result_expense() # optim

        if debug:
            print(' === _compute_budget_totals (rg_result) ===')
        
        if groupby_analytic: # MRP
            for x in rg_result:
                aac_id = x['analytic_account_id'][0] if x['analytic_account_id'] else False
                mapped_totals[x[self._record_field]][aac_id] = [x[field] for field in total_fields]
                pivot_analytic_to_budget_type[aac_id] = x['budget_type']
        else: # PO, picking, ...
            for x in rg_result:
                mapped_totals[x[self._record_field]] = [x[field] for field in total_fields]
    
        for record in self:
            if debug:
                print(' === _compute_budget_totals (result) === ')
                print('rg_result', rg_result)
                print('mapped_totals', mapped_totals.get(record.id, []))
            
            record._compute_budget_totals_one(
                mapped_totals.get(record.id, {} if groupby_analytic else []),
                pivot_analytic_to_budget_type,
            )

    def _compute_budget_totals_one(
            self, totals,
            pivot_analytic_to_budget_type = {}, field_suffix = '' # for MRP
        ):
        """ Totals calculation of single `self` so it can be
            overwritten in MRP

            :arg totals: {aac_id: sum_reserved, sum_expense, sum_gain}
            :option pivot_analytic_to_budget_type: {aac_id: budget_type} for MRP
            :option field_suffix: for MRP
        """
        # totals
        (sum_reserved, sum_expense, sum_gain) = (0.0, 0.0, 0.0)
        totals_iter = totals.values() if isinstance(totals, dict) else totals # for MRP
        for (reserved, expense, gain) in totals_iter:
            sum_reserved += reserved
            sum_expense += expense
            sum_gain += gain

        # set sums fields
        fields = {
            'total_budget_reserved': sum_reserved,
            'total_expense_valued': sum_expense,
            'amount_gain': sum_gain,
        }
        for k, v in fields.items():
            if k + field_suffix in self:
                self[k + field_suffix] = v
            elif k in self:
                self[k] = v

    #===== Reservation provisioning =====#
    def _populate_budget_analytics(self, rg_result):
        """ Automatically choose budget analytics on document update """
        debug = False

        self = self.with_context(budget_analytic_ids_computed_auto=True) # for purchase
        mapped_analytics = self._get_mapped_project_analytics()
        for record in self:
            project_budgets = mapped_analytics.get(record.project_id.id, []) if record.project_id else []
            auto_budget_centers = record._get_auto_budget_analytic_ids(rg_result)
            record.budget_analytic_ids = list(set(auto_budget_centers) & set(project_budgets)) or False
            # `or False` is needed to remove all budget if empty

            if debug:
                print(' == _populate_budget_analytics == ')
                print('project_budgets', project_budgets)
                print('record._get_auto_budget_analytic_ids()', record._get_auto_budget_analytic_ids(rg_result))
                print('list(set(record._get_auto_budget_analytic_ids()) & set(project_budgets))', list(set(record._get_auto_budget_analytic_ids(rg_result)) & set(project_budgets)))
                print('record.budget_analytic_ids', record.budget_analytic_ids)

    def _get_mapped_project_analytics(self, domain_arg=[]):
        """ Get available budgets, per project
            :option `domain_arg`: used in `carpentry.budget.balance`
        """
        return {
            # don't use `read_group` to benefit cache
            project.id: project.budget_line_ids.filtered_domain(domain_arg).analytic_account_id.ids
            for project in self.project_id
        }
        # debug = False
        # domain = [('project_id', 'in', self.project_id.ids)]
        # if domain_arg:
        #     domain = expression.AND([domain, domain_arg])
        
        # rg_result = self.env['account.move.budget.line'].read_group(
        #     domain=domain,
        #     groupby=['project_id'],
        #     fields=['analytic_account_id:array_agg'],
        # )
        # if debug:
        #     print(' == _get_mapped_project_analytics == ')
        #     print('domain', domain)
        #     print('rg_result', rg_result)
        # return {x['project_id'][0]: x['analytic_account_id'] for x in rg_result}

    def _get_record_fields(self):
        self.env['carpentry.budget.reservation']._get_record_fields()

    @api.model
    def _get_key(self, rec=None, vals={}, mode='budget'):
        """ Return a tuple like:
            (project_id, launch_id, aac_id, [record_id])

            :option `rec`:  record of `reservation`, `available` or `remaining`, ...
            :option `vals`: same, from a _read_group
                            either `rec` or `vals` must be provided
            
            :return: tuple like: (project_id, launch_id, aac_id, [record_id])
                     computed from `rec` or `vals` depending asked `fields`
        """
        debug = False
        if debug:
            print(' ==== start _get_key ==== ')
        
        if mode == 'budget':
            fields = ['project_id', 'launch_id', 'analytic_account_id']
        elif mode == 'full':
            fields = ['project_id', 'launch_id', 'analytic_account_id', self._record_field]
        else:
            raise exceptions.UserError(_("Operation not supported."))

        key = []
        for field in fields:
            has_field = hasattr(rec, rec._record_field) if rec else self._record_field in vals
            if has_field:
                id_ = rec[field].id if rec else vals[field] and vals[field][0]
                key.append(id_)
        
        return tuple(key)
    
    def _get_launch_ids(self):
        """ Overwritten in `carpentry.budget.balance` """
        return self.launch_ids._origin.ids + [False]

    def _get_mapped_existing_reservations(self):
        """ Return existing reservation lines in `self` records,
            to prevent duplicates reservation lines
        """
        debug = False
        if debug:
            print(' === _get_mapped_existing_reservations === ')
        return [
            self._get_key(reservation, mode='full')
            for reservation in self.reservation_ids
        ]

    def _get_mapped_possible_reservations(self):
        """ Ensure not dummy reservations lines are created
            in the matrix launchs*budget centers,
            i.e. we only create lines where budget can
            actually *exists*
        """
        debug = False
        if debug:
            print(' == _get_mapped_possible_reservations (start) ==')
        
        Available = self.env['carpentry.budget.available']
        domain = [
            ('record_res_model', 'in', ['project.project', 'carpentry.group.launch']),
            ('launch_id', 'in', self._get_launch_ids()),
            ('analytic_account_id', 'in', self.budget_analytic_ids._origin.ids),
        ]
        rg_result = Available._read_group(
            domain=domain,
            groupby=['project_id', 'launch_id', 'analytic_account_id'],
            fields=[],
            lazy=False,
        )
        mapped_available = [
            self._get_key(vals=x, mode='budget')
            for x in rg_result
        ]
        
        if debug:
            print(' == _get_mapped_possible_reservations (debug) ==')
            print('analytics', self.env['account.analytic.account'].search_read(
                [('is_project_budget', '=', True)], ['name']
            ))
            print('domain', domain)
            print('availables', Available.search_read(
                domain=[('budget_type', '=', 'service')],
                fields=['analytic_account_id', 'amount_subtotal_valued'],
            ))
            print('mapped_available', mapped_available)

        return mapped_available

    def _populate_budget_reservations(self, rg_result):
        """ Populate budget matrix (create/delete)
            and auto-reservation (write) when:
            - (un)selecting launches
            - (un)selecting budget centers

            :arg `rg_result`: output of `_get_rg_result_expense`, which is consuming, so passed
                              from `_populate_budget_analytics`, already generates it
        """
        debug = False
        if debug:
            print(' ===== _populate_budget_reservations (start) ===== ')

        if not self.filtered_domain(self._get_domain_can_reserve_budget()):
            return

        mapped_possibles = self._get_mapped_possible_reservations() # from Available
        mapped_existings = self._get_mapped_existing_reservations() # from Reservation

        if debug:
            print(' ===== _populate_budget_reservations (result) ===== ')
            print('mapped_possibles', mapped_possibles)
            print('mapped_existings', mapped_existings)

        vals_list = []
        for record in self:
            # 1. Auto-update reservation amounts
            for aac_id in record.budget_analytic_ids._origin.ids:
                for launch_or_project_id in record._get_launch_ids(): # launch or project
                    # don't create reservation line if not possible or already existing
                    key_budget = (record.project_id.id, launch_or_project_id, aac_id)
                    key_resa = tuple(list(key_budget) + [record.id])
                    if not key_budget in mapped_possibles or key_resa in mapped_existings:
                        continue

                    vals_list += [record._get_reservation_vals(*key_budget)]
                    mapped_existings.append(key_resa) # for next iter
            
            # 2. Remove reservations of unselected launchs or budget centers,
            #    or where there is no 'initially available' budget anymore
            #    (!) after 1. because either `launch_ids` or `budget_analytic_ids`
            #    can be computed fields from affectations
            record.reservation_ids.filtered(lambda resa: (
                self._get_key(resa, mode='budget') not in mapped_possibles
                or resa.analytic_account_id not in record.budget_analytic_ids._origin
            )).unlink()

        self.env['carpentry.budget.reservation'].create(vals_list)
        self._auto_update_budget_distribution(rg_result) # recompute `amount_reserved`
        if debug:
            print('vals_list', vals_list)

    def _get_reservation_vals(self, project_id, launch_id, aac_id, amount_reserved=0.0):
        self.ensure_one()
        aac = self.budget_analytic_ids.browse(aac_id)
        launch = self.launch_ids.browse(launch_id)

        return {
            # m2o
            'project_id': project_id,
            'launch_id': launch_id,
            'analytic_account_id': aac_id,
            self._record_field: self.id,
            'budget_type': aac.budget_type,
            'date': self.date_budget,
            # sequence
            'sequence_launch': launch.sequence,
            'sequence_aac': aac.sequence,
            'sequence_record': self.sequence if hasattr(self, 'sequence') else self._get_default_sequence(),
            # values
            'amount_reserved': amount_reserved,
            'active': all([
                self._get_default_active(),
                self.project_id.active,
                launch.active if launch else True,
                aac.active,
            ]),
        }
    
    def _get_default_sequence(self):
        """ Default `sequence` for records's **reservations**
            If not `sequence` field: `create_date` to int
        """
        self.ensure_one()
        if hasattr(self, 'sequence'):
            return self.sequence
        else:
            date_seq = self._origin.create_date if self.id else datetime.now()
            return calendar.timegm(date_seq.timetuple())
    
    def _get_default_active(self):
        """ Default `active` for records's **reservations**
            This includes state: *cancel* records are not taken into account
            (both expense & reservations)
        """
        active = self.active if hasattr(self, 'active') else True
        if hasattr(self, 'state'):
            active &= self.state not in ('cancel')
        return active

    #===== Business logics =====#
    def _auto_update_budget_distribution(self, rg_result):
        """ Automatically fill in amounts of budget reservations,
            spreading the record's expense (per budget & launch)
            according to remaining budget.

            It considers:
             - total real cost, per budget analytic (e.g. in the order_line or stock moves),
                for `budget_analytic_ids`
             - maximized to the remaining budget of selected launches, per analytic
        """
        debug = False
        if debug:
            print(' === _auto_update_budget_distribution (start) === ')
            
        if not self._get_reservations_auto_update():
            return
        
        prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        mapped_remaining_budget = self._get_remaining_budget() # independant of `self.id`
        total_by_analytic = self._get_total_budgetable_by_analytic(rg_result)

        # Group by total of remaining budget per analytic
        # (removes `launch_id` in the key),
        # to be able to spread expense per launch's remaining budget
        mapped_total_remaining_budget = defaultdict(float)
        for (project_id, launch_id, analytic_id), remaining_budget in mapped_remaining_budget.items():
            if launch_id:
                mapped_total_remaining_budget[(project_id, analytic_id)] += remaining_budget
        
        for record in self:
            for reservation in record._get_reservations_auto_update():
                key_budget = reservation._get_key(reservation, mode='budget')
                key_resa = tuple(list(key_budget) + [record.id])

                # in € or h
                key_expense = (record.id, reservation.analytic_account_id.id)
                total_price = total_by_analytic.get(key_expense, 0.0)
                remaining_budget = mapped_remaining_budget.get(key_budget, 0.0)

                # 1. Spread the expense over launch (if needed)
                expense_spread = total_price
                if reservation.launch_id:
                    key_total = (reservation.project_id.id, reservation.analytic_account_id.id)
                    total_budget = mapped_total_remaining_budget.get(key_total)
                    #                 launch remaining / aac's total remaining
                    expense_spread *= (remaining_budget / total_budget) if total_budget else 0.0
                
                # 2. Maximize expense to remaining available budget
                amount = float_round(
                    min(expense_spread, remaining_budget),
                    precision_digits=prec, rounding_method='HALF-UP',
                )
                reservation.amount_reserved = max(0.0, amount) # prevent negative reservation

                if debug:
                    print(' === _auto_update_budget_distribution (result) === ')
                    print('key', key_resa)
                    print('expense_spread', expense_spread)
                    print('reservation.amount_reserved', reservation.amount_reserved)
        
        # update totals
        # ALY - 2025-11-03: commented to see if _compute is triggered anyway
        # if self._context.get('carpentry_no_compute_budget_totals'):
        #     self_compute = self.with_context(carpentry_no_compute_budget_totals=False)
        #     self_compute._compute_budget_totals(rg_result)
    
    def _get_reservations_auto_update(self):
        """ Filters reservations for which `amount_reserved` should not be updated
            (inherited for workorders)
        """
        return self.reservation_ids
    
    def _get_total_budgetable_by_analytic(self, rg_result):
        """ :return: Dict like {analytic_id: real cost} where *real cost* is:
            - for PO: untaxed total of lines with *consumable* products only
            - for MO: addition of:
                > move_raw_ids values
                > workcenter hours
            - etc.
            :return: Dict like {(record_id, analytic_id): charged amount (brut)}
        """
        debug = False
        if debug:
            print(' ==== _get_total_budgetable_by_analytic ==== ')
        
        # rg_result = self._get_rg_result_expense(
        #     rg_fields=['amount_expense'],
        #     rg_groupby=['project_id', 'analytic_account_id']
        # )
        return {
            (
                x[self._record_field][0],
                x['analytic_account_id'] and x['analytic_account_id'][0],
            ): x['amount_expense']
            for x in rg_result
            if bool(x['amount_expense']) # filter existing reservation without expense (anymore)
        }
    def _get_auto_budget_analytic_ids(self, rg_result):
        """ In `_populate_budget_analytics`, for `budget_analytic_ids` to follow the expense
            (!) result is not yet filtered with *only* the budgets existing in the `project_id` 
            Can be overriden in *records* to improve perf
        """
        return [
            aac_id for (_, aac_id) in self._get_total_budgetable_by_analytic(rg_result)
        ]

    def _get_remaining_budget(self):
        """ Calculate [Initial Budget] - [Reservation], per launch & analytic
             without record's reservation
             (!) Always in *BRUT*
             
            :return: mapped_dict with `key_budget`
        """
        debug = False
        if debug:
            print(' === _get_remaining_budget === ')

        domain = [
            ('project_id', 'in', self.project_id._origin.ids),
            ('launch_id', 'in', self._get_launch_ids()),
            (self._record_field, 'not in', self[self._record_field].ids),
        ]
        rg_result = self.env['carpentry.budget.remaining'].read_group(
            domain=domain,
            groupby=['project_id', 'launch_id', 'analytic_account_id'],
            fields=['amount_remaining:sum(amount_subtotal)'],
            lazy=False,
        )
        return {
            self._get_key(vals=x, mode='budget'): x['amount_remaining']
            for x in rg_result
        }

    #===== Button =====#
    def save_refresh(self):
        self.readonly_budget_analytic_ids = False
        self.readonly_reservation = False
    
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
            ('record_res_model', 'in', ['project.project', 'carpentry.group.launch']),
            ('project_id', '=', self.project_id.id),
            ('launch_id', 'in', self._get_launch_ids()),
        ]
        return action
    
    def open_budget_available(self):
        """ Opens available budget report *groupped by positions* and filtered on record's launches """
        return self.action_open_budget(
            xml_id='action_open_budget_available',
            context={'search_default_filter_groupby_launch': 1}
        )
    
    def open_remaining_budget(self):
        return self.action_open_budget('action_open_budget_report_remaining')
    
    def button_force_refresh(self):
        """ Recomputes budget reservation amounts with
            automatic distribution of expense to budget centers
        """
        rg_result = self._get_rg_result_expense()
        self._auto_update_budget_distribution(rg_result)

    #===== Views =====#
    def _get_view_carpentry_config(self):
        """
            Let possibility of several templating in same form, for MRP
            :return: list of dict
        """
        return [
            {
                'templates': {
                    'alert_banner': self._carpentry_budget_alert_banner_xpath,
                    'smart_button': self._carpentry_budget_smartbuttons_xpath,
                    'notebook_page': self._carpentry_budget_notebook_page_xpath,
                },
                'params': {
                    'model_name': self._name,
                    'model_description': self._description,
                    'fields_suffix': '', # for MRP
                    'budget_types': self._get_budget_types(),
                    'budget_choice': self._carpentry_budget_choice,
                    'sheet_name': self._carpentry_budget_sheet_name,
                    'last_valuation_step': self._carpentry_budget_last_valuation_step,
                    'button_refresh': True,
                }
            },
        ]

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type != "form":
            return res
        
        View = self.env["ir.ui.view"]
        doc = etree.XML(res["arch"])
        all_models = res["models"].copy() # {modelname(str) ➔ fields(tuple)}
        changed = False

        for config in self._get_view_carpentry_config():
            # add the 3 templates to the `form` view
            for template, xpath in config['templates'].items():
                # custom layout (e.g. tasks)
                nodes = xpath and doc.xpath(xpath)
                if not nodes:
                    continue

                # configurable fields (for MRP)
                # fields names are passed as `params` so it's almost transparent
                # to call the param in the Qweb view, like `t-att-name="reservation_ids"`
                fields = [
                    'reservation_ids', 'total_budget_reserved', 'other_expense_ids',
                    'budget_analytic_ids',
                    'amount_gain', 'amount_loss', 'total_expense_valued', 'total_budgetable',
                    'is_temporary_gain', 'show_gain', 'budget_unit', 'text_no_reservation',
                ]
                config['params']['fields'] = {}
                for f in fields:
                    f_suffixed = f + config['params']['fields_suffix']
                    config['params']['fields'][f] = f_suffixed if f_suffixed in self else f
                
                # generate the template's arch
                template = 'carpentry_position_budget.carpentry_budget_template_' + template
                str_element = self.env["ir.qweb"]._render(template, config['params'])
                new_node = etree.fromstring(str_element)
                new_arch, new_models = View.postprocess_and_fields(new_node, self._name)
                new_node = etree.fromstring(new_arch)

                # place it
                for node in nodes:
                    for new_element in new_node:
                        node.addnext(new_element)
                _merge_view_fields(all_models, new_models)

                changed = True
        
        if changed:
            res["arch"] = etree.tostring(doc)
            res["models"] = frozendict(all_models)
        
        return res

def _merge_view_fields(all_models: dict, new_models: dict):
    """Merge new_models into all_models. Both are {modelname(str) ➔ fields(tuple)}."""
    for model, view_fields in new_models.items():
        if model in all_models:
            all_models[model] = tuple(set(all_models[model]) | set(view_fields))
        else:
            all_models[model] = tuple(view_fields)
