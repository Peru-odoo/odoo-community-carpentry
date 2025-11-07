# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from odoo.osv import expression
from collections import defaultdict

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
    # quantities
    amount_reserved = fields.Float(
        string="Budget reservation",
        digits='Product Unit of Measure',
        group_operator='sum',
    )
    amount_initially_available = fields.Float(
        string="Budget initially available",
        digits='Product Unit of Measure',
        group_operator='sum',
        compute='_compute_quantities',
    )
    amount_reserved_siblings = fields.Float(
        string="Budget reserved by other documents",
        digits='Product Unit of Measure',
        group_operator='sum',
        compute='_compute_quantities',
    )
    amount_remaining = fields.Float(
        string="Remaining budget",
        digits='Product Unit of Measure',
        group_operator='sum',
        compute='_compute_quantities',
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
        fields = ['project_id'] + self._get_record_fields()
        for field in fields:
            model = field.replace('_id', '')
            _not, record_field = '', ''
            if field == 'project_id':
                _not = 'NOT'

            self.env.cr.execute(f"""
                DROP INDEX IF EXISTS idx_carpentry_budget_reservation_integrity_{model};
                
                CREATE UNIQUE INDEX idx_carpentry_budget_reservation_integrity_{model} 
                ON carpentry_budget_reservation (analytic_account_id, project_id {record_field})
                WHERE (project_budget IS {_not} TRUE);
            """)
    
    #===== Constrain: no overconsumption =====#
    @api.onchange('amount_reserved')
    @api.constrains(lambda self: self._get_depends_quantities())
    def _constrain_amount_reserved(self):
        reservation = fields.first(self.filtered(lambda x: x.amount_remaining < 0))
        if reservation:
            raise exceptions.ValidationError(_(
                "The reserved budget is higher than the one available in the project:\n\n"
                "Launchs: %(launchs)s\n"
                "Budget centers: %(analytics)s\n"
                "Initial budget in the project: %(initial_budget)s\n"
                "Budget reserved on other documents: %(reservation_other)s\n"
                "Budget reservation in the current document: %(reservation_current)s\n"
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
    
    def _compute_record_field(self):
        fields = self._get_record_fields()
        first = self.first(self)._found_record_field_one(fields)
        if fields[0] != first: # optim: put 1st record_field at beginning of fields
            fields = [first] + [x for x in fields if x != first]
        
        for reservation in self:
            reservation.record_field = reservation._found_record_field_one(fields)
    def _found_record_field_one(self, fields):
        for field in fields:
            if bool(self[field]):
                return field
        return False

    def _update_record_fields(self):
        """ Called from `carpentry.budget.mixin` """
        for reservation in self:
            record = reservation._origin[self.record_field]

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
        return [
            ('project_id', 'in', self.project_id._origin.ids),
            ('analytic_account_id', 'in', self.analytic_account_id._origin.ids),
            ('launch_id', 'in', [False] + self.launch_id._origin.ids),
        ] + (
            [(self.record_field, operator, self[self.record_field]._origin.ids)]
            if with_record else []
        )
    
    @api.depends('analytic_account_id', 'launch_id')
    def _compute_amount_expense_gain_valued(self):
        """ Display *real* expense (and gain) for information,
            in budget reservation table, from
            view `carpentry.budget.expense.distributed`
        """
        print(' ==== start _compute_amount_expense_gain_valued ==== ')
        fields = ('analytic_account_id', 'launch_id', self.record_field)
        Expense = self.env['carpentry.budget.expense.distributed'].with_context(active_test=False)
        rg_result = Expense.read_group(
            domain=self._get_domain_budget_reservation(),
            fields=['amount_expense_valued:sum', 'amount_gain:sum'],
            groupby=['project_id', 'launch_id', 'analytic_account_id', self.record_field],
            lazy=False,
        )
        mapped_data = {
            tuple([data[field] and data[field][0] for field in fields]):
            (data['amount_expense_valued'], data['amount_gain'])
            for data in rg_result
        }
        for reservation in self:
            key = reservation._get_key(rec=reservation)
            (
                reservation.amount_expense_valued, reservation.amount_gain,
            ) = mapped_data.get(key, (0.0, 0.0))

    def _get_depends_quantities(self):
        return [
            'amount_reserved', 'launch_id', 'analytic_account_id',
        ] + self._get_record_fields()
    
    @api.depends(lambda self: self._get_depends_quantities())
    def _compute_quantities(self):
        """ Budget mode: default to 'brut'
            can be enforced in the view with context="{'brut_or_valued': 'brut' or 'valued'}"
        """
        self = self.with_context(active_test=True)
        
        valued = bool(self._context.get('brut_or_valued', 'brut') == 'valued')
        amount_fields = ['amount_subtotal'] + (['amount_subtotal_valued'] if valued else [])
        rg_fields = ['project_id', 'launch_id', 'analytic_account_id']

        rg_result = self.env['carpentry.budget.remaining']._read_group(
            domain=self._get_domain_budget_reservation(with_section=False) + [
                '|',
                ('record_res_model', 'in', ['project.project', 'carpentry.group.launch']), # exclude positions
                ('state', '=', 'reservation'),
            ],
            groupby=['state'] + rg_fields,
            fields=[x + ':sum' for x in amount_fields],
            lazy=False,
        )
        mapped_budgets = {'budget': {}, 'reservation': {}}
        for x in rg_result:
            key = tuple([x[field] and x[field][0] for field in rg_fields])
            budgets = tuple([x[field] for field in amount_fields])
            mapped_budgets[x['state']][key] = budgets

        for reservation in self:
            amount_reserved = reservation._origin.amount_reserved
            key = tuple([x[field] and x[field][0] for field in rg_fields])

            reservation.amount_initially_available = mapped_budgets['budget'].get(key, 0.0)
            reservation.amount_reserved_siblings = (
                mapped_budgets['reservation'].get(key, 0.0) - amount_reserved
            )
            reservation.amount_remaining = (
                reservation.amount_initially_available
                - reservation.amount_reserved_siblings
                - reservation.amount_reserved
            )
