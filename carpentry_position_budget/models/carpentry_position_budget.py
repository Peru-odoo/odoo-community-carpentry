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
        help='Only relevant for budget in hours',
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
        'project_id.date_start', 'project_id.date',
    )
    def _compute_value(self):
        """ - Services (work-force) are valued as per company's value table (on project's lifetime)
            - Goods value is directly in `amount` 
        """
        for budget in self:
            analytic = budget.analytic_account_id
            budget.value = analytic and analytic._value_amount(
                budget.amount,
                budget.project_id.date_start,
                budget.project_id.date,
            )
        
        # Also revalue budget reservation
        # affectations = self.env['carpentry.group.affectation'].search(
        #     domain=[
        #         ('project_id', 'in', budget.project_id.ids),
        #         ('group_id', 'in', budget.analytic_account_id.ids),
        #         ('group_res_model', '=', 'account.analytic.account'),
        #     ]
        # )
        # affectations._compute_quantity_affected_valued()

    #===== Helpers: add or erase budget of a position (at budget import) =====#
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
