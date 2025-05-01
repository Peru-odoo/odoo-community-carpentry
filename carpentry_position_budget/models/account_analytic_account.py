# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools.misc import format_amount
from odoo.tools import float_is_zero
from collections import defaultdict
from pprint import pprint

class AccountAnalyticAccount(models.Model):
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

    def _get_default_line_type(self):
        if self.budget_type in ['service', 'production', 'installation']:
            return 'workforce'
        return super()._get_default_line_type()
    
    def _compute_budget_unit(self):
        for analytic in self:
            analytic.budget_unit = 'h' if analytic._get_default_line_type() == 'workforce' else '€' 
    
    #===== Native ORM methods =====#
    def _search(self, domain, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self._context.get('analytic_display_budget'):
            order = 'budget_type, name'
        return super()._search(domain, offset, limit, order, count, access_rights_uid)

    #==== Affectation matrix =====#
    def _get_quantities_available(self, affectations=None, section=None, launchs=None, brut_or_valued=None):
        """ Called from `carpentry.group.affectation`, to compute `quantity_available`
             field on budget reservation matrix.
            It depends on:
            - the Project or Launch (affectation.record_ref) *and*
            - the Budget type (affectation.group_ref) *and*
            - the PO or MO (affectation.section_ref)
        """
        section = fields.first(affectations).section_ref
        launch_ids = affectations.filtered(lambda x: x.record_res_model == 'carpentry.group.launch').mapped('record_id')
        launchs = self.env['carpentry.group.launch'].sudo().browse(launch_ids)
        available = self._get_available_budget_initial(launchs, section, brut_or_valued)
        return available
        # remaining = self._get_remaining_budget(launchs, section, brut_or_valued)
        # return remaining

    def _get_remaining_budget_by_analytic(self, launchs, section, brut_or_valued=None):
        """ Group remaining budget by `analytic`,
            according to required `launchs` & `section`
        """
        remaining_budget = self._get_remaining_budget(launchs, section, brut_or_valued)
        groupped_data = defaultdict(float)
        for key in remaining_budget:
            _, _, analytic_id = key
            groupped_data[analytic_id] += remaining_budget[key]
        return groupped_data

    def _get_remaining_budget(self, launchs, section=None, brut_or_valued=None):
        """ Calculate [Initial Budget] - [Reservation], per launch & analytic
            :arg self:       only those analytics budgets are searched
            :arg launchs:    filters searched budget to only those launches
                             note: Global Cost are always searched, because per-project
            :option section: PO or MO record
            :option mode: None, 'brut' or 'valued'
                if `None`, it will switch between 'brut' and 'valued' depending the budget, e.g.
                (hours) will use `brut`
                (amount) will use `valued`
            :return: Dict like:
                {('launch' or 'project', launch-or-project.id, analytic.id): remaining available budget}
        """
        available = self._get_available_budget_initial(launchs, section, brut_or_valued)
        reserved = self._get_sum_reserved_budget(launchs, section, sign=-1)

        # careful: browse all keys and all rows of both `brut-or-valued` and `reserved`
        # since they might be budget without reservation *or* reservation without budget
        remaining = reserved.copy() # are values are negative (`sign=-1`)
        for key, amount_available in available.items():
            remaining[key] = remaining.get(key, 0.0) + amount_available
        
        return remaining
    
    def _get_available_budget_initial(self,
                                        launchs,
                                        section=None,
                                        brut_or_valued=None,
                                        project_budgets=True,
                                        groupby_budget='analytic_account_id'
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
                ('carpentry.group.launch',  launch.id, analytic.id): amount, ...}, # per-position budget
                ('project.project', project.id, analytic.id): amount, ...}, # global budget (per project)
                ...
            }
        """
        # === 1. Budget from launches ===
        # budget mode: default to 'brut'
        # can be enforced in the view with context="{'brut_or_valued': 'brut' or 'valued'}"
        brut_or_valued = brut_or_valued or self._context.get('brut_or_valued', 'brut')

        # Budget from launches (computed)
        available = self.env['carpentry.position.budget'].sudo().sum(
            quantities=launchs._get_quantities(),
            groupby_group=['group_id'],
            groupby_budget=groupby_budget,
            domain_budget=[('analytic_account_id', 'in', self.ids)] if self.ids else [],
            brut_or_valued=brut_or_valued,
        )
        # adapt dict's key
        available = {
            ('carpentry.group.launch', group_id_, groupby_value_): amount
            for group_id_, budget_dict in available.items()
            for groupby_value_, amount in budget_dict.items()
        }

        # === 2. Budget from the project (not computed) ===
        if project_budgets:
            # note: Global-Cost brut are only in € (not 'h'), like Fournitures
            project_ids = (section.project_id if section else launchs.project_id)._origin
            rg_result = self.env['account.move.budget.line'].sudo().read_group(
                domain=[('project_id', 'in', project_ids.ids), ('is_computed_carpentry', '=', False)],
                groupby=['type', 'project_id'] + ([groupby_budget] if groupby_budget else []),
                fields=['balance:sum'] + (['qty_balance:sum'] if brut_or_valued == 'brut' else []),
                lazy=False
            )
            for item in rg_result:
                # Add global-cost budget to `brut` & `valued`
                groupby_value_ = (
                    item[groupby_budget][0] if hasattr(item[groupby_budget], '__iter__')
                    else item[groupby_budget]
                )

                key = ('project.project', item['project_id'][0], groupby_value_)
                if not key in available:
                    available[key] = 0.0
                budget_line_field = (
                    'qty_balance' if item['type'] != 'amount' and brut_or_valued == 'brut'
                    else 'balance'
                )
                available[key] += item[budget_line_field]
        
        return available
    
    def _get_sum_reserved_budget(self, launchs, section=None, sign=1, groupby_budget='group_id'):
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
        domain_launch = launchs._get_domain_affect('record')
        domain_project = [
            ('record_res_model', '=', 'project.project'),
            ('record_id', 'in', project_ids_),
        ]
        domain = expression.OR([domain_launch, domain_project])
        if section:
            section.ensure_one()
            domain = expression.AND([domain, ['|',
                ('section_res_model', '!=', section._name),
                ('section_id', '!=', section.id),
            ]])
        
        # 2. Fetch budget reservation (consumption)
        rg_result = self.env['carpentry.group.affectation'].read_group(
            domain=domain,
            groupby=['record_model_id', 'record_id', groupby_budget],
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
            (mapped_model_name.get(x['record_model_id'][0]), x['record_id'], x[groupby_budget]):
            x['quantity_affected'] * sign
            for x in rg_result
        }
