# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from odoo.osv import expression

class CarpentryBudgetReservation(models.Model):
    """ This model is quite similar to `carpentry.affectation`,
        but for budget reservation from Launchs & Project
        instead than position's quantity affectation from Lots & Phases
    """
    _name = "carpentry.budget.reservation"
    _description = "Budget reservation"
    _order = "project_budget DESC, sequence_aac, sequence_launch, sequence_record"
    _log_access = False

    #===== Fields =====#
    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Project',
        readonly=True,
        required=True,
        ondelete='cascade',
    )
    launch_id = fields.Many2one(
        comodel_name='carpentry.group.launch',
        string='Launch',
        required=False,
        ondelete='restrict',
    )
    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Budget',
        required=True,
        ondelete='restrict',
    )
    budget_unit = fields.Char(compute='_compute_budget_unit_type', compute_sudo=True)
    budget_type = fields.Selection(
        selection=lambda self: self.env['account.analytic.account']._fields['budget_type'].selection,
        compute='_compute_budget_unit_type',
        store=True,
    )
    currency_id = fields.Many2one(related='project_id.currency_id')
    # sequence
    project_budget = fields.Boolean(
        # used in _order
        compute='_compute_project_budget',
        store=True,
    )
    sequence_launch = fields.Integer(
        string='Launch sequence',
        related='launch_id.sequence',
        store=True,
    )
    sequence_aac = fields.Integer(
        string='Analytic account sequence',
        related='analytic_account_id.sequence',
        store=True,
    )
    # records
    balance_id = fields.Many2one(
        comodel_name='carpentry.budget.balance',
        string='Balance',
        ondelete='cascade',
    )
    # record fields
    record_field = fields.Char(string='Record field', compute='_compute_record_field')
    sequence_record = fields.Integer(string='Record sequence',)
    date = fields.Date(string='Date', copy=False,)
    active = fields.Boolean(string='Active', copy=False,)
    # amounts
    amount_reserved = fields.Float(
        string="Budget reservation",
        digits='Product Unit of Measure',
        group_operator='sum',
    )
    amount_initially_available = fields.Float(
        string="Budget initially available",
        digits='Product Unit of Measure',
        group_operator='sum',
        compute='_compute_amounts',
    )
    amount_reserved_siblings = fields.Float(
        string="Budget reserved by other documents",
        digits='Product Unit of Measure',
        group_operator='sum',
        compute='_compute_amounts',
    )
    amount_remaining = fields.Float(
        string="Remaining budget",
        digits='Product Unit of Measure',
        group_operator='sum',
        compute='_compute_amounts',
    )
    amount_expense_valued = fields.Monetary(
        string="Expense",
        group_operator='sum',
        compute='_compute_amount_expense_gain_valued',
        help="Distribution of expense on this launch and budget center",
    )
    amount_gain = fields.Monetary(
        string='Gain',
        group_operator='sum',
        compute='_compute_amount_expense_gain_valued',
        help='Budget reservation - Real expense',
    )

    #===== Index (+unique) & constraints =====#
    def init(self):
        super().init()
        
        # project & launch reservations index (also ensures unicity)
        fields = self._get_record_fields()
        for field in fields:
            model = field.replace('_id', '')
            self.env.cr.execute(f"""
                DROP INDEX IF EXISTS idx_carpentry_budget_reservation_integrity_{model};
                
                CREATE UNIQUE INDEX idx_carpentry_budget_reservation_integrity_{model} 
                ON carpentry_budget_reservation (project_id, launch_id, analytic_account_id, {field});
            """)
    
    #===== Constrain: no overconsumption =====#
    @api.onchange('amount_reserved')
    @api.constrains(lambda self: self._depends_amounts())
    def _constrain_amount_reserved(self):
        reservation = fields.first(self.filtered(lambda x: x.amount_remaining < 0))
        if reservation:
            print('self', self.read(['analytic_account_id', 'launch_id', 'amount_reserved']))
            raise exceptions.ValidationError(_(
                "The reserved budget is higher than the one available in the project:\n\n"
                "Launchs: %(launchs)s\n"
                "Budget centers: %(analytics)s\n"
                "Initial budget in the project: %(initial_budget)s\n"
                "Budget reserved on other documents: %(reservation_other)s\n"
                "Temptative of budget reservation: %(reservation_current)s\n"
                "Overconsumption: %(overconsumption)s",
                launchs=' ,' . join(reservation.launch_id.mapped('name')),
                analytics=' ,' . join(reservation.analytic_account_id.mapped('name')),
                initial_budget=reservation.amount_initially_available,
                reservation_other=reservation.amount_reserved_siblings,
                reservation_current=reservation.amount_reserved,
                overconsumption=-1.0 * reservation.amount_remaining,
            ))

    #===== Compute =====#
    @api.depends('launch_id')
    def _compute_project_budget(self):
        for reservation in self:
            reservation.project_budget = not bool(reservation.launch_id)
    
    @api.depends('analytic_account_id')
    def _compute_budget_unit_type(self):
        budget_unit_forced = '€' if self._context.get('brut_or_valued') == 'valued' else None
        
        for reservation in self:
            reservation.budget_unit = budget_unit_forced or reservation.analytic_account_id.budget_unit
            reservation.budget_type = reservation.analytic_account_id.budget_type
    
    #===== Compute: record field =====#
    def _get_record_fields(self):
        """ To inherit """
        return ['balance_id']
    
    @api.model
    def _get_key(self, **kwargs):
        return self.env['carpentry.budget.mixin']._get_key(**kwargs)
    
    @api.depends(lambda self: self._get_record_fields())
    def _compute_record_field(self):
        """ :return: like 'balance_id' or 'purchase_id' or ... """
        record_fields = self._get_record_fields()
        first = fields.first(self)._found_record_field_one(record_fields)
        if record_fields[0] != first: # optim: put 1st record_field at beginning of fields
            record_fields = [first] + [x for x in record_fields if x != first]
        
        for reservation in self:
            reservation.record_field = reservation._found_record_field_one(record_fields)
    def _found_record_field_one(self, fields):
        for field in fields:
            if bool(self[field]):
                return field
        return False

    def _update_record_fields(self):
        """ Called from `carpentry.budget.mixin` """
        for reservation in self:
            record = reservation._origin[reservation.record_field]

            reservation['sequence_record'] = record._get_default_sequence()
            reservation['active'] = record._get_default_active()
            reservation['date'] = (
                record.date_budget
                if record and hasattr(record, 'date_budget')
                else False
            )

    #===== Compute: amounts =====#
    def _get_domain_budget_reservation(self, exclude=False, with_record=True):
        operator = 'not in' if exclude else 'in'
        base_domain = [
            ('project_id', 'in', self.project_id._origin.ids),
            ('analytic_account_id', 'in', self.analytic_account_id._origin.ids),
            ('launch_id', 'in', [False] + self.launch_id._origin.ids),
        ]
        if not with_record:
            return base_domain
        
        domain_records = []
        for record_field in self.mapped('record_field'):
            domain_records = expression.OR([
                domain_records,
                [(record_field, operator, self[record_field]._origin.ids)]
            ])
        return base_domain + domain_records

    def _depends_amounts(self):
        return (
            ['amount_reserved',
             'project_id', 'launch_id', 'analytic_account_id',]
            + self._get_record_fields()
        )
    @api.depends(lambda self: self._depends_amounts())
    def _compute_amounts(self):
        """ Budget mode: default to 'brut'
            can be enforced in the view with context="{'brut_or_valued': 'brut' or 'valued'}"
        """
        if self._context.get('carpentry_budget_no_compute'): # optim
            # (!) those are fake values!
            # they are re-computed after creation, on `amount_reserved` write (auto-reservation)
            self.amount_initially_available = 0.0
            self.amount_reserved_siblings = 0.0
            self.amount_remaining = 0.0
            return
        
        self = self.with_context(active_test=True)

        self.flush_model(['amount_reserved'])
        domain=self._get_domain_budget_reservation(with_record=False) + [
            '|',
            ('record_res_model', 'in', ['project.project', 'carpentry.group.launch']), # exclude positions
            ('state', '=', 'reservation'),
        ]
        _valued = '_valued' if self._context.get('brut_or_valued', 'brut') == 'valued' else ''
        amount_field = 'amount_subtotal' + _valued
        rg_fields = ['project_id', 'launch_id', 'analytic_account_id']
        rg_result = self.env['carpentry.budget.remaining']._read_group(
            domain=domain,
            groupby=['state'] + rg_fields,
            fields=[amount_field + ':sum', 'ids:array_agg(id)', 'aggr:array_agg(' + amount_field + ')'],
            lazy=False,
        )
        mapped_budgets = {'budget': {}, 'reservation': {}}
        for x in rg_result:
            key = tuple([x[field] and x[field][0] for field in rg_fields])
            mapped_budgets[x['state']][key] = x[amount_field]

        debug = False
        if debug:
            print(' == _compute_amounts == ')
            print('reservation', self.search_read([], rg_fields + ['balance_id', 'purchase_id', 'amount_reserved']))
            print('domain', domain)
            print('search_domain', self.env['carpentry.budget.remaining'].search_read(domain, ['state'] + rg_fields + [amount_field]))
            print('rg_result', rg_result)
            print('mapped_budgets', mapped_budgets)
        
        for reservation in self:
            amount_reserved = reservation._origin.amount_reserved
            key = tuple([x[field] and x[field][0] for field in rg_fields])

            reservation.amount_initially_available = mapped_budgets['budget'].get(key, 0.0)
            reservation.amount_reserved_siblings = (
                -1 * mapped_budgets['reservation'].get(key, 0.0) - amount_reserved
            )
            reservation.amount_remaining = (
                reservation.amount_initially_available
                - reservation.amount_reserved_siblings
                - reservation.amount_reserved
            )

            if debug:
                print('amount_reserved', amount_reserved)
                print('amount_inially_available', mapped_budgets['budget'].get(key, 0.0))
                print('mapped_budget[reservation]', mapped_budgets['reservation'].get(key, 0.0))
                print('amount_reserved_siblings', reservation.amount_reserved_siblings)
                print('amount_remaining', reservation.amount_remaining)

    @api.depends('analytic_account_id', 'launch_id')
    def _compute_amount_expense_gain_valued(self):
        """ Display *real* expense (and gain) for information,
            in budget reservation table, from
            view `carpentry.budget.expense.distributed`
        """
        debug = False
        rg_groupby = ['launch_id', 'analytic_account_id'] + list(set(self.mapped('record_field')))
        Expense = self.env['carpentry.budget.expense.distributed'].with_context(active_test=False)
        rg_result = Expense.read_group(
            domain=self._get_domain_budget_reservation(),
            fields=['amount_expense_valued:sum', 'amount_gain:sum'],
            groupby=rg_groupby,
            lazy=False,
        )
        mapped_data = {
            tuple([x[field] and x[field][0] for field in rg_groupby]):
            (x['amount_expense_valued'], x['amount_gain'])
            for x in rg_result
        }
        if debug:
            print(' == _compute_amount_expense_gain_valued == ')
            print('mapped_data', mapped_data)
        for reservation in self:
            key = tuple([reservation[field].id for field in rg_groupby])
            (
                reservation.amount_expense_valued, reservation.amount_gain,
            ) = mapped_data.get(key, (0.0, 0.0))
            if debug:
                print('key', key)
