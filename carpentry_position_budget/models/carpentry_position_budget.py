# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from collections import defaultdict

class CarpentryPositionBudget(models.Model):
    _name = 'carpentry.position.budget'
    _description = 'Position Budget'

    # primary keys
    project_id = fields.Many2one(
        related='position_id.project_id',
        store=True,
        index='btree_not_null',
    )
    position_id = fields.Many2one(
        comodel_name='carpentry.position',
        string='Position',
        required=True,
        index='btree_not_null',
        ondelete='cascade',
        domain="[('project_id', '=', project_id)]"
    )
    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Budget Category',
        required=True,
        ondelete='restrict',
        index='btree_not_null',
        help='Used to rapproach incomes, charges and budget in accounting reports.',
        domain="""[
            ('is_project_budget', '=', True),
            '|', ('company_id', '=', company_id), ('company_id', '=', False)
        ]"""
    )
    # for search view
    lot_id = fields.Many2one(
        related='position_id.lot_id'
    )

    # budget amount/value
    budget_type = fields.Selection(
        # needed to discrepency `goods` vs `service`
        related='analytic_account_id.budget_type',
        store=True # for groupby
    )
    amount = fields.Float(
        # depending `budget_type`, either a currency amount, or a quantity
        string='Unitary Amount',
        default=0.0,
        required=True,
    )
    quantity = fields.Integer(
        related='position_id.quantity',
        readonly=False, # so it's exportable with *Importable field only*
                        # but XML view restore it with attr readonly="1"
        help="Position's quantity in the project",
    )
    value = fields.Monetary(
        string='Unit Value',
        currency_field='currency_id',
        compute='_compute_value',
        help='Only relevant for budget in hours'
    )

    company_id = fields.Many2one(
        related='project_id.company_id'
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id'
    )

    #===== Constrain =====#
    _sql_constraints = [(
        "position_analytic",
        "UNIQUE (position_id, analytic_account_id)",
        "A position cannot receive twice a budget from the same analytic account."
    )]


    #===== Compute =====#
    @api.depends(
        'amount',
        'analytic_account_id',
        'analytic_account_id.timesheet_cost_history_ids',
        'analytic_account_id.timesheet_cost_history_ids.hourly_cost',
        'analytic_account_id.timesheet_cost_history_ids.starting_date',
    )
    def _compute_value(self):
        """ - Services (work-force) are valued as per company's value table (on project's lifetime)
            - Goods value is directly in `amount` 
        """
        for budget in self:
            budget.value = budget.sudo()._value_amount(budget.amount)
    
    def _value_amount(self, amount):
        self.ensure_one()

        line_type = self.analytic_account_id._get_default_line_type() or 'amount'

        if line_type == 'workforce':
            budget_id = fields.first(self.project_id.budget_ids)
            return self.analytic_account_id._value_workforce(amount, budget_id)
        else:
            return amount

    #===== Helpers: add or erase budget of a position =====#
    def _add_budget(self, vals_list_budget):
        self._write_budget(vals_list_budget, erase_mode=False)
    def _erase_budget(self, vals_list_budget, force=False):
        self._write_budget(vals_list_budget, erase_mode=True, erase_force=force)
    
    def _to_vals(self, replace_keys={}):
        """ Convert recordset of this model to its vals
            Useful to render `vals_list_budget` from a recordset of `carpentry.position.budget`
            
            :option replace_keys: vals dict to force-replace `vals` in `vals_list`
                                  E.g.: to re-affect budget of 1 position to another 
            :return: list of dict `vals_list`
        """
        return [{
            'position_id': replace_keys.get('position_id', budget.position_id.id),
            'analytic_account_id': replace_keys.get('analytic_account_id', budget.analytic_account_id.id),
            'amount': budget.amount
        } for budget in self]
    
    def _write_budget(self, vals_list_budget, erase_mode=False, erase_force=False):
        """ Write/add in existing budget or create new budgets 

            :param vals_list_budget: `vals_dict` of this model
            :param mode_erase:  if True,  `amount` is written in place of any existing
                                 budget, or created if no budget
                                if False, `amount` is added to existing budget
            :param erase_force: if True, the existing non-updated budgets are removed
        """

        # get existing budget, to route between `write()` or `create()`
        mapped_existing_ids = {(x.position_id.id, x.analytic_account_id.id): x for x in self}
        to_create, to_delete = [], self

        # write/sum
        for vals in vals_list_budget:
            primary_key = (vals.get('position_id'), vals.get('analytic_account_id'))
            budget = mapped_existing_ids.get(primary_key)

            if budget:
                budget.amount = vals.get('amount') if erase_mode else budget.amount + vals.get('amount')
                to_delete -= budget # for `erase_force` if True
            else:
                to_create.append(vals)
        
        # create
        self.create(to_create)

        # delete
        if erase_mode and erase_force:
            to_delete.unlink()


    #===== Helpers: budget computation =====#
    def sum(self,
            quantities={},
            groupby_budget='analytic_account_id',
            domain_budget=[],
            groupby_group=['position_id'],
            brut_or_valued='both'
        ):
        """ Multiplies each items' value in `quantities` by the its position's unitary budget

            :option quantities:
                Output of `_get_quantities()` from `carpentry.group.affectation.mixin`.
                 list of of dict like [{tuple: qty}] where `tuple` is a frozenset, like:
                 ([('position_id', id), ('launch_id', id)])
            :option groupby_budget:
                For values grouping, see `_get_position_unitary_budget()`
                If None, only 1 dict (valued) is returned
            :option groupby_group:
                For output grouping by keys of `quantities`
        
            :return: dicts keeping the keys format of `quantities`, useful for Sale Order or Fab Order where same
                     position may appear twice in different Launches
                     See `compute_subtotal_and_group()`
        """
        if self._context.get('import_budget_no_compute'):
            return
        
        # Get `budget_ids` if `quantities` were given but `self` is empty
        if not self.ids:
            position_ids = [dict(key)['position_id'] for key in quantities.keys()]
            self = self.search([('position_id', 'in', position_ids)] + domain_budget)

        # If no groupby, return only valued budget
        if not groupby_group:
            brut_or_valued = 'valued'

        # Get unitary budget
        unitary_budgets = self._get_position_unitary_budget(groupby_budget, brut_or_valued)
        subtotal = self._compute_subtotal_and_group(unitary_budgets, quantities, groupby_group, brut_or_valued)
        return subtotal
    
    def _get_position_unitary_budget(self, groupby_budget='analytic_account_id', brut_or_valued='both'): 
        """ Gets unitary budget per position as per 'groupby_budget' details
            
            :option self: is a recordset of `carpentry.position.budget` that should be filtered before on only wanted `groupby_budget`
            :option groupby_budget: any relevant field for this model to be groupped on, like: `analytic_account_id`, `budget_type`

            :return: 2 dicts of unitary budget per `position_id`
             - 1st dict: brut, ie. `amount` fields (currency for *goods* and a quantity for *service*)
             - 2nd dict: valued amounts, ie. money for both
             
             Dicts' format:
              - keys: `position_id`
              - values:
                > `Float` if groupby_budget=None (and both dicts are the same) --> valued amounts only
                > dict like {id_ of groupby_budget field, like analytic_account_id: groupped sum of `amount` or `value` depending the dict}
        """
        # 1. Prepare output format
        if not groupby_budget:
            default_value = 0.0
            brut_or_valued = 'valued'
        else:
            # get possible values of `groupby_budget` in self
            # this is why `self` should be filtered on only wanted `groupby_budget` field
            # /!\ values can be int (ids_) or str (like for `budget_type`, which is a selection field)
            key_ids = self.mapped(groupby_budget)
            try:
                default_value = {(key if isinstance(key, str) else key.id): 0.0 for key in key_ids}
            except:
                raise exceptions.ValidationError(_(
                    "Missing the configuration of %s to compute the position's budget.",
                    groupby_budget
                ))
        
        # 2. If no groupby_budget, sum all (valuted) budgets by `position_id`
        if not groupby_budget:
            unitary_budgets = defaultdict(float)
            for budget in self:
                unitary_budgets[budget.position_id.id] += budget.value
            return unitary_budgets
        # 3. Sum-group unitary budgets by position, by `groupby_budget`
        else:
            compute_value = brut_or_valued in ['valued', 'both']
            unitary_budgets = {'brut': {}, 'valued': {}}
            for budget in self:
                # manage M2n field (e.g. `analytic_account_id` (.id) vs `budget_type` (str))
                field_value = budget[groupby_budget]
                key = field_value.id if hasattr(field_value, '_name') else field_value

                # Create key or get it
                brut = unitary_budgets['brut'].setdefault(budget.position_id.id, default_value.copy())
                brut[key] += budget.amount
                
                # performance: don't value hours if not needed
                if compute_value:
                    valued = unitary_budgets['valued'].setdefault(budget.position_id.id, default_value.copy())
                    valued[key] += budget.value
        
        return unitary_budgets if brut_or_valued == 'both' else unitary_budgets[brut_or_valued]
    
    def _compute_subtotal_and_group(self, unitary_budgets, quantities, groupby_group, brut_or_valued):
        """ Calculate subtotal budgets for each items of `quantities`, by multipling items' qty by position's unitary budget
             *and* groupby the items according to `groupby_group` fields
            
            :option unitary_budgets:
                {position_id: {key1: amount, ...}}
            :quantities:
                {{'position_id': x, 'grouping_id1': y, ...}: qty}
            
            :return:
                dict of 2 items if brut_or_valued == 'both', or direcly a dict like:
                {new_key: values of `unitary_budgets` * qty value in `quantities`} where `new_key`:
                 - if `groupby_group` has only 1 item, `new_key` is the id of this record (eg. a project_id, phase_id, ...)
                 - else, `new_key` follows the same format than `quantities` keys (frozenset)
        """
        if brut_or_valued == 'both':
            brut, valued = unitary_budgets
            return (
                self._compute_subtotal_and_group(brut, quantities, groupby_group, brut_or_valued='brut'),
                self._compute_subtotal_and_group(valued, quantities, groupby_group, brut_or_valued='valued'),
            )

        subtotals = {}
        for key, qty in quantities.items():
            # Prepare the key (c.f. return format)
            dict_key = dict(key)
            if len(groupby_group) == 1:
                new_key = dict_key[groupby_group[0]]
            else:
                new_key = frozenset({field: dict_key[field] for field in groupby_group}.items())
            
            # Sum-group: item's qty * position's unitary_budget
            position_id = dict_key['position_id']
            if not new_key in subtotals:
                subtotals[new_key] = defaultdict(int)
            for key_budget, unitary_budget in unitary_budgets.get(position_id, {}).items(): # no comprehension list here because of +=
                subtotals[new_key][key_budget] += qty * unitary_budget
            
        return subtotals
