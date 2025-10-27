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
    _order = "project_budget DESC, sequence_aac, sequence_launch, sequence_section"
    _log_access = False

    #===== Fields methods =====#
    def _selection_section_res_model(self):
        return [
            (x['model'], x['name'])
            for x in self.env['ir.model'].search_read([], ['model', 'name'])
        ]

    def _selection_record_res_model(self):
        models = self._selection_section_res_model()
        return [
            (model, name) for model, name in models
            if model in ('project.project', 'carpentry.group.launch')
        ]

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
    project_budget = fields.Boolean(compute='_compute_project_budget', store=True,)
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
    # section (PO, MO, invoice, picking, task, ...)
    section_id = fields.Many2oneReference(
        # (!) actually an `Integer` field, so not .dot notation
        model_field='section_res_model',
        string='Section ID',
        readonly=True,
        index=False,
    )
    section_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Section Model ID',
        ondelete='cascade',
        index=False,
    )
    section_res_model = fields.Char(
        string='Section Model',
        related='section_model_id.model',
    )
    # section fields
    sequence_section = fields.Integer(
        string='Section sequence',
        compute='_compute_section_fields',
        store=True,
    )
    date = fields.Date(
        string='Date',
        compute='_compute_section_fields',
        store=True,
        copy=False,
    )
    active = fields.Boolean(
        string='Active',
        compute='_compute_section_fields',
        store=True,
        copy=False,
    )
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
        config = {'project': '', 'launch': 'NOT'}
        for model, _not in config.items():
            self.env.cr.execute(f"""
                DROP INDEX IF EXISTS idx_carpentry_budget_reservation_integrity_{model};
                
                CREATE UNIQUE INDEX idx_carpentry_budget_reservation_integrity_{model} 
                ON carpentry_budget_reservation ({model}_id, analytic_account_id, section_id, section_model_id)
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
    
    @api.depends('section_id', 'section_model_id')
    def _compute_section_fields(self):
        if not self: return # optim
        self.section_model_id.ensure_one()

        model_name = fields.first(self).section_res_model
        sections = self.env[model_name].browse(
            self._origin.mapped('section_id')
        )

        for reservation in self:
            section = sections.browse(reservation._origin.section_id)
            
            reservation['sequence_section'] = section._get_default_sequence()
            reservation['active'] = section._get_default_active()
            reservation['date'] = (
                section.date_budget
                if section and hasattr(section, 'date_budget')
                else False
            )

    #===== Compute: amounts =====#
    @api.depends(
        'analytic_account_id', 'launch_id',
        'section_id', 'section_model_id',
    )
    def _compute_amount_expense_gain_valued(self):
        """ Display *real* expense (and gain) for information,
            in budget reservation table, from
            view `carpentry.budget.expense.distributed`
        """
        domain = [
            ('project_id', 'in', self.project_id.ids),
            ('launch_id', 'in', [False] + self.launch_id.ids),
            ('analytic_account_id', 'in', self.analytic_account_id.ids),
            ('section_id', 'in', self.mapped('section_id')),
            ('section_model_id', 'in', self.section_model_id.ids),
        ]
        Expense = self.env['carpentry.budget.expense.distributed'].with_context(active_test=False)
        rg_result = Expense.read_group(
            domain=domain,
            fields=['amount_expense_valued:sum', 'amount_gain:sum'],
            groupby=['launch_id', 'analytic_account_id', 'section_id', 'section_model_id'],
            lazy=False,
        )
        mapped_data = {
            (x['launch_id'] and x['launch_id'][0], x['analytic_account_id'][0], x['section_id'], x['section_model_id'][0]):
            (x['amount_expense_valued'], x['amount_gain'])
            for x in rg_result
        }
        for resa in self:
            key = (resa.launch_id.id, resa.analytic_account_id.id, resa.section_id, resa.section_model_id.id)
            (
                resa.amount_expense_valued,
                resa.amount_gain,
            ) = mapped_data.get(key, (0.0, 0.0))

    def _get_depends_quantities(self):
        return [
            'amount_reserved',
            'launch_id', 'analytic_account_id', 'section_id', 'section_model_id',
        ]
    @api.depends(lambda self: self._get_depends_quantities())
    def _compute_quantities(self):
        self = self.with_context(active_test=True)
        mapped_available = self._get_budget_initially_available()
        mapped_reserved = self._get_budget_reserved_other()

        for reservation in self:
            key = (reservation.project_id.id, reservation.launch_id.id, reservation.analytic_account_id.id)
            reservation.amount_initially_available = mapped_available.get(key, 0.0)
            reservation.amount_reserved_siblings = mapped_reserved.get(key, 0.0)
            reservation.amount_remaining = (
                reservation.amount_initially_available
                - reservation.amount_reserved_siblings
                - reservation.amount_reserved
            )
    
    def _get_budget_initially_available(self):
        """ Budget mode: default to 'brut'
            can be enforced in the view with context="{'brut_or_valued': 'brut' or 'valued'}"
        """
        valued = '_valued' if self._context.get('brut_or_valued', 'brut') == 'valued' else ''
        return self._get_budget_mapped_data(
            model='carpentry.budget.available',
            field='amount_subtotal' + valued,
            domain=self._get_domain_initially_available(),
        )
    def _get_domain_initially_available(self):
        return [
            ('group_res_model', 'in', ['project.project', 'carpentry.group.launch']), # exclude positions
            ('project_id', 'in', self.project_id.ids),
            ('launch_id', 'in', [False] + self.launch_id.ids),
        ]
    
    def _get_budget_reserved_other(self):
        return self._get_budget_mapped_data(
            model='carpentry.budget.reservation',
            field='amount_reserved',
            domain=self._get_domain_other_budget_reservation(),
        )
    def _get_domain_other_budget_reservation(self):
        return [
            ('project_id', 'in', self.project_id._origin.ids),
            ('analytic_account_id', 'in', self.analytic_account_id._origin.ids),
            ('launch_id', 'in', [False] + self.launch_id._origin.ids),
        ] + self._get_domain_exclude_sections()
    def _get_domain_exclude_sections(self, sections=None):
        """ Return a *OR* domain excluding `self` sections """
        # 1. Organize `section_ids` per `section_model_id`
        IrModel = self.env['ir.model']
        mapped_section_ids = defaultdict(list)
        if sections:
            for section in sections:
                mapped_section_ids[IrModel._get_id(section._name)].append(section.id)
        else:
            for reservation in self:
                mapped_section_ids[reservation.section_model_id.id].append(reservation.section_id)

        # 2. Generate the domain
        domain = []
        for model_id, section_ids in mapped_section_ids.items():
            domain += ['|',
                ('section_model_id', '!=', model_id),
                ('section_id', 'not in', section_ids),
            ]
        
        return (['|'] + domain) if len(domain) > 3 else domain

    def _get_budget_mapped_data(self, model, field, domain):
        """ Shortcut of `rg_result` for `carpentry.budget.available` and `carpentry.budget.reservation` """
        rg_result = self.env[model]._read_group(
            domain=domain,
            groupby=['project_id', 'launch_id', 'analytic_account_id'],
            fields=[field + ':sum'],
            lazy=False,
        )
        return {
            (x['project_id'][0], x['launch_id'] and x['launch_id'][0], x['analytic_account_id'][0]): x[field]
            for x in rg_result
        }
