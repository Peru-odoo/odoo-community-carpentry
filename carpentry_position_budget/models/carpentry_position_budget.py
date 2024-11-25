# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
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
        ondelete='cascade'
    )
    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Budget Category',
        required=True,
        ondelete='restrict',
        index='btree_not_null',
        help='Used to rapproach incomes, charges and budget in accounting reports.'
    )
    # for search view
    lot_id = fields.Many2one(
        related='position_id.lot_id'
    )

    # amount
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Product',
        related='analytic_account_id.product_tmpl_id', # analytic's default product
    )
    uom_id = fields.Many2one(
        related='product_tmpl_id.uom_id'
    )
    type = fields.Selection(
        # needed to discrepency `goods` vs `service`
        related='product_tmpl_id.type'
    )
    detailed_type = fields.Selection(
        # needed for groupby
        related='product_tmpl_id.detailed_type',
    )
    amount = fields.Float(
        # either a currency amount (goods `type`) or a quantity in uom (workforce, service `type`)
        string='Amount',
        default=0.0,
        required=True,
    )
    value = fields.Monetary(
        string='Value',
        currency_field='currency_id',
        compute='_compute_value'
    )
    currency_id = fields.Many2one(
        related='project_id.company_id.currency_id'
    )

    #===== Constrain =====#
    _sql_constraints = [(
        "position_analytic",
        "UNIQUE (position_id, analytic_account_id)",
        "A position cannot receive twice a budget from the same analytic account."
    )]


    #===== Compute =====#
    @api.depends('amount', 'analytic_account_id.product_tmpl_id')
    def _compute_value(self):
        """ - Services (work-force) are valued as per company's value table (on project's lifetime)
            - Goods value is directly in `amount` 
        """
        for budget in self:
            budget.value = budget._value_qty(budget.amount) if budget.type == 'service' else budget.amount
    
    def _value_qty(self, qty):
        self.ensure_one()
        return self.product_tmpl_id._value_qty(qty, fields.first(self.project_id.budget_ids))


    #===== Helpers: add or erase budget of a position =====#
    def _add_budget(self, vals_list_budget):
        self._write_budget(vals_list_budget, erase_mode=False)
    def _erase_budget(self, vals_list_budget, force=True):
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
            :param mode_erase: if False, `amount` is added to existing budget
            :param erase_force: if False, the existing non-updated budgets are kept
        """
        print('=== _write_budget ===')
        print('vals_list_budget', vals_list_budget)
        print('erase_mode', erase_mode)
        print('erase_force', erase_force)

        # get existing budget, to route between `write()` or `create()`
        mapped_existing_ids = {(x.position_id.id, x.analytic_account_id.id): x for x in self}
        to_create, to_delete = [], self
        print('mapped_existing_ids', mapped_existing_ids)

        # write/sum
        for vals in vals_list_budget:
            primary_key = (vals.get('position_id'), vals.get('analytic_account_id'))
            budget = mapped_existing_ids.get(primary_key)
            print('vals', vals)
            print('primary_key', primary_key)
            print('budget', budget)

            # note: no need to convert uom here, since `product_tmpl_id` is the same for all `analytic_account_id` (related field)
            if budget:
                budget.amount = amount if erase_mode else budget.amount + amount
                to_delete -= budget # for `erase_force` if True
            else:
                to_create.append(vals)
        
        # create
        print('to_create', to_create)
        self.create(to_create)

        # delete
        if erase_mode and erase_force:
            to_delete.unlink()


    #===== Helpers: budget computation =====#
    def _get_position_unitary_budget(self, groupby_budget='analytic_account_id'): 
        """ Gets unitary budget per position as per 'groupby_budget' details
            
            :option self: is a recordset of `carpentry.position.budget` that should be filtered before on only wanted `groupby_budget`
            :option groupby_budget: any relevant field for this model to be groupped on, like: `analytic_account_id`, `detailed_type`

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
        else:
            # get possible values of `groupby_budget` in self
            # this is why `self` should be filtered on only wanted `groupby_budget` field
            # /!\ values can be int (ids_) or str (like for `detailed_type`, which is a selection field)
            key_ids = self.mapped(groupby_budget)
            default_value = {(key if isinstance(key, str) else key.id): 0.0 for key in key_ids}
        
        # 2. Sum-group unitary budgets by position, by `groupby_budget`
        unitary_budgets_brut, unitary_budgets_valued = {}, {}
        for budget in self:
            # Create key or get it
            brut = unitary_budgets_brut.setdefault(budget.position_id.id, default_value.copy())
            valued = unitary_budgets_valued.setdefault(budget.position_id.id, default_value.copy())

            if not groupby_budget: # if we don't want any details of budget (just 1 amount per position) => value the services
                brut += budget.value
                valued += budget.value
            else:
                brut[budget[groupby_budget]] += budget.amount
                valued[budget[groupby_budget]] += budget.value
        
        return unitary_budgets_brut, unitary_budgets_valued
    
    
    def sum(self, quantities={}, groupby_budget='analytic_account_id', domain_budget=[], groupby_group=['position_id']):
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
        
        # Get `budget_ids` if `quantities` were given but `budget_ids` in self are empty
        if not self.ids:
            position_ids = [dict(key)['position_id'] for key in quantities.keys()]
            self = self.search([('position_id', 'in', position_ids)] + domain_budget)

        # Get unitary budget
        brut_unitary, valued_unitary = self._get_position_unitary_budget(groupby_budget)

        # Sumprod unitary_budget * quantities, per item of `quantities` (~affectation) and group the result per `groupby_group`
        brut_subtotal = self._compute_subtotal_and_group(brut_unitary, quantities, groupby_group)
        valued_subtotal = self._compute_subtotal_and_group(valued_unitary, quantities, groupby_group)
        return valued_subtotal if not groupby_budget else brut_subtotal, valued_subtotal
        
    def _compute_subtotal_and_group(self, unitary_budgets, quantities, groupby_group):
        """ Calculate subtotal budgets for each items of `quantities`, by multipling items' qty by position's unitary budget
             *and* groupby the items according to `groupby_group` fields
            
            :option unitary_budgets:
                {position_id: {key1: amount, ...}}
            :quantities:
                {{'position_id': x, 'grouping_id1': y, ...}: qty}
            
            :return:
                {new_key: values of `unitary_budgets` * qty value in `quantities`} where `new_key`:
                 - if `groupby_group` has only 1 item, `new_key` is the id of this record (eg. a project_id, phase_id, ...)
                 - else, `new_key` follows the same format than `quantities` keys (frozenset)
        """
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
