# -*- coding: utf-8 -*-

from re import A
from odoo import models, fields, api, exceptions, _, Command
from odoo.osv import expression
from odoo.tools import float_round
from collections import defaultdict

class CarpentryGroupAffectation(models.Model):
    """ ==== Description ====
            This model holds **all** the relations between the Carpentry *Groups* Models. Single table because:
            * M2M classic fields does not allow additional field in the relation table, which is always required here (eg. qty, sequences)
            * allow shared inverse methods of `carpentry.group.affectation.mixin` to inverse **temp** to **real** affectations 

        ==== Reminder table ====
            model (Carp. Doc.)       `group`            `record`                       `section_id`
             carpentry.group.phase    phase_id            position_id (M2M)              lot_id
             carpentry.group.launch   launch_id           affectation_id of phase (O2m)  phase_id
             purchase.order           analytic_id         launch_id (M2M)                po_id

        ==== Affectations patterns ====
            - [VERY SIMPLE] Standard O2m (like `launch_ids`) from the model to `carpentry.group.launch`
                 -> For `carpentry.plan` and `task.group`
            - [SIMPLE] When only `record`+`client` are used. `record` points either to a `position_id`
                 -> for Phases: 2 dimensions only + `affected_quantity` in the relation
                 -> Can even be *only* a O2m (for plan) rather than a M2M (for Phases, and Task.Group)
            - [NESTED AFFECTATION] When `affectation_id` is used in place of `record`
                 -> for Launches: 3 dimensions, shown in a 2D-table where lines are grouped
                 -> in x2many_2d_matrix, lines are other affectations. They are groupped by `client` of parent affectation
            - [BUDGET RESERVATION] See `carpentry_budget` module
                 -> 3-dimension: `client` is not in the x2many_2d_matrix but actually *is* the form
                 -> 3rd field is either `affectation_id` for MRP or `record` (launch_id) for SaleOrder
    """
    _name = "carpentry.group.affectation"
    _description = "Position Affectation"
    _order = "seq_section, seq_group, sequence"
    _rec_name = "display_name"
    _log_access = False
    _carpentry_affectation = True

    #===== Fields methods ======#
    def _selection_group_res_model(self):
        model_ids = self.env['ir.model'].sudo().search([])
        return [
            (model.model, model.name)
            for model in model_ids
            if (
                model.model in self.env
                and hasattr(self.env[model.model], '_carpentry_affectation')
                and self.env[model.model]._carpentry_affectation
            )
        ]

    def _selection_record_res_model(self):
        return [
            # position affectation to phase & launch
            ('carpentry.position', 'Position'),
            ('carpentry.group.affectation', 'Affectation'),

            # buget reservation (po and wo)
            ('carpentry.group.launch', 'Launch'),
            ('project.project', 'Project'),
        ]
    
    def _selection_section_res_model(self):
        return self._selection_group_res_model()
    
    # Base
    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Project',
        readonly=True,
        required=True,
        ondelete='cascade'
    )
    currency_id = fields.Many2one(
        related='project_id.company_id.currency_id'
    )
    active = fields.Boolean(default=True)

    # group: the record holding the affecation (in column in x2m_2d_matrix)
    group_id = fields.Many2oneReference( # actually an `Integer` field, so not .dot notation
        model_field='group_res_model',
        string='Group ID',
        readonly=True,
        required=True,
        index='btree_not_null'
    )
    group_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Group Model ID',
        ondelete='cascade',
        index='btree_not_null',
    )
    group_res_model = fields.Char(
        string='Group Model',
        related='group_model_id.model',
    )
    group_ref = fields.Reference(
        selection='_selection_group_res_model',
        compute='_compute_group_ref',
    )
    seq_group = fields.Integer()

    # record: the affected record (in line in x2m_2d_matrix)
    record_id = fields.Many2oneReference( # actually an `Integer` field, so not .dot notation
        model_field='record_res_model',
        string='Record ID',
        readonly=True,
        required=True,
        index='btree_not_null',
    )
    record_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Record Model ID',
        ondelete='cascade',
        index='btree_not_null',
    )
    record_res_model = fields.Char(
        string='Record Model',
        related='record_model_id.model',
    )
    record_ref = fields.Reference(
        selection='_selection_record_res_model',
        compute='_compute_record_ref',
    )
    sequence = fields.Integer()

    # section: the *optional* record used for ordering/grouping lines of x2m_2d_matrix
    section_id = fields.Many2oneReference( # actually an `Integer` field, so not .dot notation
        model_field='section_res_model',
        string='Section ID',
        readonly=True,
        index='btree_not_null',
    )
    section_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Section Model ID',
        ondelete='cascade',
        index='btree_not_null',
    )
    section_res_model = fields.Char(
        string='Section Model',
        related='section_model_id.model',
    )
    section_ref = fields.Reference(
        selection='_selection_section_res_model',
        compute='_compute_section_ref',
        search='_search_section_ref',
    )
    seq_section = fields.Integer()

    # Nested/children affectations: when the affectation's parent is another affectation
    affectation_ids = fields.One2many(
        comodel_name='carpentry.group.affectation',
        inverse_name='record_id',
        string='Children Affectations',
        domain=[('record_res_model', '=', 'carpentry.group.affectation')]
    )
    position_id = fields.Many2one(
        comodel_name='carpentry.position',
        string='Position',
        compute='_compute_position_id',
        store=True,
    )
    
    # Affected Quantity (when `record_ref` is a position), i.e. for Phases
    quantity_affected = fields.Float(
        string="Affected quantity",
        default=False,
        digits='Product Unit of Measure',
        group_operator='sum',
    )
    quantity_available = fields.Float(
        # Position Quantity (for Phase) or Available budget (for PO, MO)
        # /!\ `quantity_available` is needed *here* for real-time correct value
        string="Available",
        compute='_compute_quantity_available',
        group_operator='sum'
    )
    quantity_remaining_to_affect = fields.Float(
        string='Remaining to affect',
        compute='_compute_quantity_remaining_to_affect',
        group_operator='sum',
        help="[Available quantity in the project] - [Sum of quantities already affected]",
    )
    sum_affected_siblings = fields.Float(
        string='Sum of affected to neighbors',
        compute='_compute_sum_affected_siblings',
        group_operator='sum',
    )

    # for launch
    affected = fields.Boolean(
        default=True,
        index='btree_not_null',
    )
    is_affectable = fields.Boolean(
        compute='_compute_is_affectable',
    )
    
    _sql_constraints = [(
        "group_record",
        "UNIQUE (group_id, group_model_id, record_id, record_model_id, section_id, section_model_id)",
        "Integrity error (unicity of 1 group and 1 record per cell)."
    )]

    #===== Global compute =====#
    def _compute_display_name(self):
        for affectation in self:
            affectation.display_name = affectation._get_display_name()
    def _get_display_name(self, display_with_suffix=True):
        """ Affectation `display_name` is `record_ref`'s

            When lines are grouped by a section (eg. lots for phases's positions),
            `display_name` is:
             - prefixed by section's `display_name` and
             - suffixed by `quantity_affected` (affectation) or `quantity` (position)
            
            Context key `display_with_suffix` avoids pre- and suf-fixing
        """
        self.ensure_one()
        display_with_suffix = self._context.get('display_with_suffix', display_with_suffix)
        prefix, suffix = '', ''
        if display_with_suffix:
            prefix = "[%s] " % self.group_ref.display_name
            suffix = " (%s)" % int(self.quantity_affected) # int for position qty
        
        record_display = self.record_ref.with_context(display_with_suffix=False).display_name
        return prefix + record_display + suffix
    
    @api.depends('group_id', 'group_model_id')
    def _compute_group_ref(self):
        for affectation in self:
            affectation.group_ref = '%s,%s' % (affectation.group_res_model, affectation.group_id)
    @api.depends('record_id', 'record_model_id')
    def _compute_record_ref(self):
        for affectation in self:
            affectation.record_ref = '%s,%s' % (affectation.record_res_model, affectation.record_id)
    @api.depends('section_id', 'section_model_id')
    def _compute_section_ref(self):
        for affectation in self:
            affectation.section_ref = (
                '%s,%s' % (affectation.section_res_model, affectation.section_id)
                if affectation.section_id else False
            )
    
    @api.depends('record_id')
    def _compute_position_id(self):
        """ Recursively find `position_id` from `record_ref` """
        for affectation in self:
            position_id = affectation._origin.record_ref
            while position_id and position_id._name != 'carpentry.position' and hasattr(position_id, 'record_ref'):
                position_id = position_id.record_ref
            affectation.position_id = position_id if position_id._name == 'carpentry.position' else False

    #===== Constrain: can't delete if having children =====#
    @api.ondelete(at_uninstall=False)
    def _unlink_affectation_id(self):
        """ * Prevent affectation deletion when it has affectation children (i.e.
              prevent orphans affectation, like Phase)
            * Allow cascade deletion of affectations when client is a real carpentry
              record (like Launch)
        """
        if self.affectation_ids.ids:
            raise exceptions.UserError(
                _("This affectation cannot be deleted since used by another record"
                 " (like a Launch, Sale Order, Fabrication Order, ...)")
            )

    #===== Constrain: M2o-like if `_carpentry_affectation_quantity == False` =====#
    @api.depends('record_id', 'active', 'affected')
    def _compute_is_affectable(self):
        # get siblings
        rg_result = self.env[self._name].read_group(
            domain=self._get_domain_siblings(),
            groupby=['group_model_id', 'record_model_id', 'record_id'], # group per line
            fields=['siblings_ids:array_agg(id)'],
            lazy=False,
        )
        mapped_siblings_ids = {
            (x['group_model_id'][0], x['record_model_id'][0], x['record_id']): x['siblings_ids']
            for x in rg_result
        }

        # check constrain per row
        for affectation in self:
            key = (affectation.group_model_id.id, affectation.record_model_id.id, affectation.record_id)
            siblings = set(mapped_siblings_ids.get(key, [])) - set([affectation._origin.id])

            affectation.is_affectable = len(siblings) == 0
    
    @api.constrains('record_id', 'active')
    def _constrain_m2o(self):
        """ Replay a M2o constrain: prevent from 2 affectations on same row """
        self = self.with_context(active_test=False)

        # constrain only on groups not allowing M2M
        self = self.filtered(lambda x: not x.group_ref._carpentry_affectation_allow_m2m).filtered(lambda x: x.affected)
        if not self:
            return

        for affectation in self:
            if not affectation.is_affectable:
                raise exceptions.ValidationError(
                    _('One line cannot be affected to several columns (%s).', affectation.display_name)
                )
    
    def _get_siblings_parent(self):
        """ Siblings position-to-phase or affectation-to-launch
            share the same `record_ref` (i.e. `position_id` or `affectation_id`)
        """
        return self.record_ref
    
    def _get_domain_siblings(self):
        return [
            # on the same matrix
            ('group_model_id', 'in', self.group_model_id.ids),
            ('record_model_id', 'in', self.record_model_id.ids),
            # on the same line
            ('record_id', 'in', self.mapped('record_id')),
            ('active', '=', True),
            ('affected', '=', True),
        ]

    #===== Quantities & M2o: constrain & compute =====#
    @api.onchange('quantity_affected')
    @api.constrains('quantity_affected')
    def _constrain_quantity(self):
        # only for groups using qties for affectation
        if self._context.get('constrain_quantity_affected_silent'):
            return
        
        for affectation in self:
            if (
                not affectation.group_ref or
                not affectation.group_ref._carpentry_affectation_quantity
            ):
                continue

            # 2024-11 - ALY: disabled to allow `qty == 0` via affectation shortcut
            # if affectation.quantity_affected <= 0:
            #     raise exceptions.ValidationError(
            #         _("Quantity affected must be strictly greater than 0, delete it instead.")
            #     )
            if affectation.quantity_remaining_to_affect < 0:
                raise exceptions.ValidationError(_(
                    "The affected quantity is higher than the one available in the project:\n"
                    "- Records: '%s' and '%s'\n"
                    "- Total available quantity in the project: %s\n"
                    "- Affected quantity in the current item: %s\n"
                    "- Affected quantity on neighbors: %s\n"
                    "- Overconsumption: %s",
                    affectation.record_ref.name,
                    affectation.group_ref.name,
                    affectation.quantity_available,
                    affectation.quantity_affected,
                    affectation.sum_affected_siblings,
                    -1.0 * affectation.quantity_remaining_to_affect,
                ))

    def toggle_active(self):
        """ Do not put `active` field in @api.constrains, else it
            runs constrain check at PO form loading
        """
        res = super().toggle_active()
        self._constrain_quantity()
        return res
    
    @api.depends('record_id', 'group_id', 'section_id', 'active')
    def _compute_quantity_available(self):
        prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # Technically check if computation is relevant/possible
        self.group_model_id.ensure_one()
        group_res_model = fields.first(self).group_res_model
        groups_ids = self.env[group_res_model].browse(self.mapped('group_id'))
        if not groups_ids or not hasattr(groups_ids, '_get_quantities_available'):
            self.quantity_available = False
            return
        
        mapped_quantities = groups_ids._get_quantities_available(self._origin)
        for affectation in self:
            key = (affectation.record_res_model, affectation.record_id, affectation.group_id)
            affectation.quantity_available = float_round(
                mapped_quantities.get(key, 0.0), precision_digits=prec
            )
    
    @api.depends('record_id', 'quantity_affected')
    def _compute_quantity_remaining_to_affect(self):
        """ Compute remaining qty to affect for phases affectation, i.e. where
            `record_id` is a `carpentry.position`. This is needed for constrain
            on remaining_qty>0
            
            Note: we cannot use `search()` because we need real-time display of remaining_qty
            (2 affectation can be modified in `x2m_2d_matrix`)
        """
        prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        for affectation in self:
            # exclude current affectation from the sum
            affectation.quantity_remaining_to_affect = float_round(
                affectation.quantity_available
                - affectation.sum_affected_siblings
                - affectation.quantity_affected
            , precision_digits=prec)

    @api.depends('record_id', 'record_model_id')
    def _compute_sum_affected_siblings(self):
        prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        for affectation in self:
            sum_affected_siblings = 0.0
            if affectation.record_ref:
                sibling_parent = affectation._origin._get_siblings_parent()
                domain = affectation._get_domain_siblings()
                siblings = sibling_parent.affectation_ids.filtered_domain(domain) - affectation._origin
                sum_affected_siblings = sum(siblings.mapped('quantity_affected'))
            
            affectation.sum_affected_siblings = float_round(
                sum_affected_siblings, precision_digits=prec
            )
            
class CarpentryAffectationTemp(models.TransientModel):
    """
        * This model holds temporary data in right format for 'x2many_2d_matrix' widget (x_field, y_field, value_field)
        * Data are populated by a '_compute_affectation_xxxx' method from parent model (a project, sale order or fab order)
            Logic for data population is hold in the model of 'group_id', with main purpose of:
            1. read any previous affectation from 'carpentry.group.affectation' and present them to the user for modification
            2. fill the gaps of 2d matrix with default values
        * At form save, its data are processed through a '_inverse_affectation_xxx' method on parent model with main purpose to save them in
            'carpentry.group.affectation' *real* model. Mainly, the _inverse logic consists in:
            1. Matching all 'temp' records with 'real' records (if any)
            2. Take relevant actions depending on the scenario, ie. add, remove, update in *real* table 'carpentry.group.affectation'
            3. Clean this *temp* table
    """
    _name = "carpentry.group.affectation.temp"
    _inherit = ["carpentry.group.affectation"]
    _description = "Position Affectation (Temp)"
    _order = "seq_section, seq_group, sequence"
    _rec_name = "display_name"

    def _constrain_quantity(self):
        """ Neutralize this constrain in temp """
        return
    def _compute_sum_affected_siblings(self):
        return
    