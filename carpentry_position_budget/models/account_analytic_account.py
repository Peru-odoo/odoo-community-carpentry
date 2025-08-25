# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.misc import format_amount
from odoo.tools import float_is_zero

class AnalyticAccount(models.Model):
    _name = 'account.analytic.account'
    _inherit = ['account.analytic.account']
    # for Purchase & Manufacturing Orders
    _carpentry_affectation = True # to allow affectation (as `group_ref`)
    _carpentry_affectation_quantity = True # affectation by qty
    _carpentry_affectation_allow_m2m = True
    _carpentry_affectation_section = False

    #===== Fields methods =====#
    def name_get(self):
        """ Add:
            - prefix: [Budget Type] ...
            - suffix: ... remaining budget 0,00€
        """
        res = super().name_get()
        if not self._context.get('analytic_display_budget'):
            return res

        analytics = self.browse(list(dict(res).keys()))
        section_res_model, section_id = self._context.get('section_res_model'), self._context.get('section_id')
        remaining_budget = {}
        if section_res_model and section_id:
            section = self.env[section_res_model].sudo().browse(section_id)
            remaining_budget = analytics._get_remaining_budget_by_analytic(section.launch_ids, section)
        
        budget_type_selection = dict(self._fields['budget_type']._description_selection(self.env))
        res_updated = []
        for id_, name in res:
            analytic = analytics.browse(id_)

            # prefix [Budget Type]
            budget_type = _(budget_type_selection.get(analytic.budget_type))
            name = f'[{budget_type}] {name}'

            # suffix budget & clock
            amount_remaining = remaining_budget.get(id_, 0.0)
            if not float_is_zero(amount_remaining, precision_rounding=analytic.currency_id.rounding):
                amount_str = format_amount(self.env, amount_remaining, analytic.currency_id)
                if analytic.budget_unit == 'h':
                    amount_str = amount_str.replace('€', 'h')
                name += f' ({amount_str})'

            res_updated.append((id_, name))
        
        return res_updated

    #===== Fields =====#
    affectation_ids = fields.One2many(
        comodel_name='carpentry.group.affectation',
        inverse_name='group_id',
        domain=[('group_res_model', '=', _name)]
    )
    budget_type = fields.Selection(
        selection_add=[
            ('production', 'Production'),
            ('installation', 'Installation'),
            ('project_global_cost', 'Other cost'),
        ],
        ondelete={
            'production': 'set service',
            'installation': 'set service',
            'project_global_cost': 'set goods',
        }
    )
    budget_unit = fields.Char(
        compute='_compute_budget_unit'
    )
    template_line_ids = fields.One2many(
        # for domain in Interface
        comodel_name='account.move.budget.line.template',
        inverse_name='analytic_account_id'
    )

    def _get_budget_type_workforce(self):
        return ['service', 'production', 'installation']

    def _get_default_line_type(self):
        return (
            'workforce' if self.budget_type in self._get_budget_type_workforce()
            else super()._get_default_line_type()
        )
    
    def _compute_budget_unit(self):
        for analytic in self:
            analytic.budget_unit = 'h' if analytic._get_default_line_type() == 'workforce' else '€' 
    
    def _value_amount(self, amount, date_start, date_end, mapped_hourly_cost=[]):
        """ Just a conditionaly method to convert h to € *when needed*:
            - position available budget
            - reserved budget

            :option mapped_hourly_cost: There is 2 mode to value:
                a) if given (from _get_hourly_cost()) => value on a specific date, for PO, MO, ...
                b) else (no specific date): assume `amount` is spread on all `project_id`'s time
                    => use hourly_cost table between date range of project's budget
        """
        self.ensure_one()

        line_type = self._get_default_line_type() or 'amount'

        if line_type == 'workforce':
            # if not mapped_hourly_cost:
            return self._value_workforce(amount, date_start, date_end)
        else:
            return amount
    
    def _get_hourly_cost(self, date):
        """ Return the last `hourly_cost` per analytic account """
        pass
    
    #===== Native ORM methods =====#
    def _search(self, domain, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self._context.get('analytic_display_budget'):
            order = 'budget_type, name'
        return super()._search(domain, offset, limit, order, count, access_rights_uid)

    #==== Affectation matrix =====#
    def _get_quantities_available(self, affectations):
        """ Called from `carpentry.group.affectation`, to compute `quantity_available`
             field on budget reservation matrix.
            It depends on:
            - the Project or Launch (affectation.record_ref) *and*
            - the Budget type (affectation.group_ref) *and*
            - the PO or MO (affectation.section_ref)
        """
        section = fields.first(affectations).section_ref
        launchs = self.env['carpentry.group.launch'].sudo().browse(
            affectations.filtered(lambda x: x.budget_type).mapped('record_id')
        )
        return self._get_available_budget_initial(launchs, section)

    def _get_remaining_budget_by_analytic(self, launchs, section):
        """ Group remaining budget by `analytic`, according to required `launchs` & `section`
            (!!!) Always in *BRUT*

            :return: Dict like {analytic_id_: amount}
        """
        rg_result = self.env['carpentry.budget.remaining'].read_group(
            domain=[('launch_id', 'in', launchs.ids)] + self._get_budget_domain_exclude_section(section),
            groupby=['analytic_account_id'],
            fields=['quantity_affected:sum'],
        )
        return {x['analytic_account_id'][0]: x['quantity_affected'] for x in rg_result}

    def _get_budget_domain_exclude_section(self, section):
        return (
            ['|', ('state', '=', 'budget')]
            + self._get_domain_exclude_section(section)
        ) if section else []
    def _get_domain_exclude_section(self, section):
        return ['|',
            ('section_res_model', '!=', section._name),
            ('section_id', 'not in', section.ids),
        ] if section else []

    def _get_remaining_budget(self, launchs, section=None):
        """ Calculate [Initial Budget] - [Reservation], per launch & analytic
            (!!!) Always in *BRUT*
            
            :arg self:       only those analytics budgets are searched
            :arg launchs:    filters searched budget to only those launches
                             note: Global Cost are always searched, because per-project
            :option section: PO or MO record
            :return: Dict like:
                {('launch' or 'project', launch-or-project.id, analytic.id): remaining available budget}
        """
        # Prepare domain
        project_ids = (section.project_id if section else launchs.project_id)._origin
        domain = [
            ('project_id', 'in', project_ids.ids),
            ('launch_id', 'in', [False] + launchs.ids),
        ] + (
            self._get_budget_domain_exclude_section(section)
        )

        # Fetch & return data
        remaining = {}
        rg_result = self.env['carpentry.budget.remaining'].read_group(
            domain=domain,
            groupby=['project_id', 'launch_id', 'analytic_account_id'],
            fields=['quantity_affected:sum'],
            lazy=False,
        )
        for data in rg_result:
            analytic_id_ = data['analytic_account_id'][0]
            if data['launch_id']:
                key = ('carpentry.group.launch', data['launch_id'][0],  analytic_id_)
            else:
                key = ('project.project',        data['project_id'][0], analytic_id_)
            
            remaining[key] = data['quantity_affected']
        
        return remaining
    
    def _get_available_budget_initial(self,
                                        launchs,
                                        section=None,
                                        brut_or_valued=None,
                                        ):
        """ :arg launchs:
                explicit
            :option project_budgets:
                if `False`, don't compute and add global-cost budget
                (useful from carpentry planning)
            :option section:
                `section_ref` record (like PO, MO, picking) to be excluded from
                the sum. Useful to compute *remaining budgets* on POs and MOs
            :option brut_or_valued:
                `None` defaults to `context.get('brut_or_valued', 'brut')`
                 other accepted values: `brut` or `valued`
                 **IMPORTANT**: `both` is not accepted here
                 - if `brut`: unit will conditionally be `h` or `€` depending on `budget_type`
                 - if `valued`: unit will be only `€`
            :option groupby_budget:
                field to group budget by
                 - 'analytic_account_id' (default)
                 - 'budget_type' (e.g. production, installation, ...)
                 - 'group_id' (e.g. carpentry.group.launch)
            :return: Dict like (brut, valued) where each item is a dict-of-dict like:
            {
                ('carpentry.group.launch', launch.id, analytic.id): amount, ...}, # per-position budget
                ('project.project', project.id, analytic.id): amount, ...}, # global budget (per project)
                ...
            }
        """
        # Budget mode: default to 'brut'
        # can be enforced in the view with context="{'brut_or_valued': 'brut' or 'valued'}"
        brut_or_valued = brut_or_valued or self._context.get('brut_or_valued', 'brut')
        valued = bool(brut_or_valued == 'valued')
        model = 'carpentry.budget.available' + ('.valued' if valued else '')
        field = 'value' if valued else 'subtotal'

        project_ids = (section.project_id if section else launchs.project_id)._origin
        rg_result = self.env[model].read_group(
            domain=[
                ('project_id', 'in', project_ids.ids),
                ('group_res_model', 'in', ['project.project', 'carpentry.group.launch']),
                ('launch_id', 'in', [False] + launchs.ids)
            ],
            groupby=['project_id', 'launch_id', 'analytic_account_id'],
            fields=[field + ':sum'],
            lazy=False,
        )
        
        available = {}
        for data in rg_result:
            analytic_id_ = data['analytic_account_id'][0]
            if data['launch_id']:
                key = ('carpentry.group.launch', data['launch_id'][0],  analytic_id_)
            else:
                key = ('project.project',        data['project_id'][0], analytic_id_)
            
            available[key] = data[field]
        
        return available
    
    def _get_sum_reserved_budget(self, launchs, section=None, sign=1):
        """ Sum all budget reservation on project & launches
             and return it by project-or-launches & analytics
            
            :arg launchs:    explicit
            :option section: `section_ref` record (PO or MO) to be excluded from
                             the sum. Useful to compute *remaining budgets* on POs and MOs
            :option sign:    give `-1` so values are negative

            :return: Dict like result of `_get_available_budget_initial`

            Note: budget reservation are *affectation* with `record_ref` being
             `launch_id` or `project_id`, and:
                - `group_id`: analytic account
                - `section_id`: the document reserving the budget (e.g. PO or MO)
                - `quantity_affected`: the reserved budget
            
        """
        # 1. Prepare search domain
        project_ids_ = [section.project_id.id] if section else launchs.project_id.ids
        domain = [
            ('budget_type', '!=', False),
            ('project_id', 'in', project_ids_),
            '|',
                ('record_res_model', '=', 'project.project'),
                '&', launchs._get_domain_affect('record'),
        ] + (
            self._get_domain_exclude_section(section)
        )
        
        # 2. Fetch budget reservation (consumption)
        rg_result = self.env['carpentry.group.affectation'].read_group(
            domain=domain,
            groupby=['record_model_id', 'record_id', 'group_id'],
            fields=['quantity_affected:sum'],
            lazy=False
        )
        domain = [('id', 'in', [x['record_model_id'][0] for x in rg_result])]
        mapped_model_name = {
            # 'project.project' or 'carpentry.group.launch'
            model['id']: model['model']
            for model in self.env['ir.model'].sudo().search_read(domain, ['model'])
        }
        return {
            (mapped_model_name.get(x['record_model_id'][0]), x['record_id'], x['group_id']):
            x['quantity_affected'] * sign
            for x in rg_result
        }
