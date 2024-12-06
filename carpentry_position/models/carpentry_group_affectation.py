# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.osv import expression

from collections import defaultdict

class CarpentryGroupAffectation(models.Model):
    """ ==== Description ====
            This model holds **all** the relations between the Carpentry *Groups* Models. Single table because:
            * M2M classic fields does not allow additional field in the relation table, which is always required here (eg. qty, sequences)
            * allow shared inverse methods of `carpentry.group.affectation.mixin` to inverse **temp** to **real** affectations 

        ==== Reminder table ====
            model (Carp. Doc.)       `group`            `record`                      `product_id`  Value field
             carpentry.group.phase    phase_id            position_id (M2M)              -            quantity_affected
             carpentry.group.launch   launch_id           affectation_id of phase (O2m)  -            -
             sale.order               sale_order_id       launch_id (M2M)                yes          amount
             mrp.workorder            mrp_workorder_id    affectation_id of launch       yes          amount
             mrp.workcenter           mrp_workcenter_id   -                              yes          amount

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
            ('carpentry.position', 'Position'),
            ('carpentry.group.affectation', 'Affectation'),
        ]
    
    # Base
    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Project',
        readonly=True,
        required=True,
        ondelete='cascade'
    )

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
        ondelete='cascade'
    )
    group_res_model = fields.Char(
        string='Group Model',
        related='group_model_id.model',
    )
    group_ref = fields.Reference(
        selection='_selection_group_res_model',
        compute='_compute_fields_ref',
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
        ondelete='cascade'
    )
    record_res_model = fields.Char(
        string='Record Model',
        related='record_model_id.model',
    )
    record_ref = fields.Reference(
        selection='_selection_record_res_model',
        compute='_compute_fields_ref',
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
        ondelete='cascade'
    )
    section_res_model = fields.Char(
        string='Section Model',
        related='section_model_id.model',
    )
    section_ref = fields.Reference(
        selection='_selection_group_res_model',
        compute='_compute_fields_ref',
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
        ondelete='restrict'
    )
    
    # Affected Quantity (when `record_ref` is a position), i.e. for Phases
    # /!\ `quantity_position` is needed *here* for real-time correct value
    # `quantity_affected_parent` is needed for nested/children affectations (i.e. launch)
    quantity_affected = fields.Integer(
        string="Affected quantity",
        default=False,
        group_operator='sum',
        help="Quantity of the position affected to the record",
    )
    quantity_affected_parent = fields.Integer(
        compute='_compute_quantity_affected_parent',
        string='Quantity affected to parent group',
    )
    quantity_position = fields.Integer(
        string="Position quantity",
        compute='_compute_quantity_position',
        group_operator='sum',
        help="Total available quantity of this position in the project",
    )
    quantity_remaining_to_affect = fields.Integer(
        string='Remaining to affect',
        compute='_compute_quantity_remaining_to_affect',
        group_operator='sum',
        help="[Quantity of position] - [Sum position's quantity already affected in the project]",
    )
    
    _sql_constraints = [(
        "group_record",
        "UNIQUE (group_id, group_model_id, record_id, record_model_id)",
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
            suffix = " (%s)" % self.quantity_affected
        
        record_display = self.record_ref._get_display_name(display_with_suffix=False)
        return prefix + record_display + suffix
    
    def _compute_fields_ref(self):
        for affectation in self:
            affectation.group_ref = '%s,%s' % (affectation.group_res_model, affectation.group_id)
            affectation.record_ref = '%s,%s' % (affectation.record_res_model, affectation.record_id)
            affectation.section_ref = '%s,%s' % (affectation.section_res_model, affectation.section_id) if affectation.section_id else False

    def _compute_quantity_affected_parent(self):
        for affectation in self:
            affectation.quantity_affected_parent = (
                'quantity_affected' in affectation.record_ref
                and affectation.record_ref.quantity_affected
            )
    
    def _compute_position_id(self):
        """ Recursively find `position_id` from `record_ref` """
        for affectation in self:
            position_id = affectation.record_ref
            while position_id and position_id._name != 'carpentry.position':
                position_id = position_id.record_ref
            affectation.position_id = position_id

    #===== Constrain: can't delete if children =====#
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
    @api.constrains('record_id')
    def _constrain_m2o(self):
        """ Replay a M2o constrain: prevent from 2 affectations on same row """
        is_temp = bool(self._name == 'carpentry.group.affectation.temp')
        _filter = (lambda x: x.affected) if is_temp else (lambda x: True)
        
        # constrain only on groups not allowing M2M
        self = self.filtered(lambda x: not x.group_ref._carpentry_affectation_allow_m2m).filtered(_filter)
        if not self:
            return

        # get siblings
        domain = [
            # on the same matrix
            ('group_model_id', 'in', self.group_model_id.ids),
            ('record_model_id', 'in', self.record_model_id.ids),
            # on the same line
            ('record_id', 'in', self.mapped('record_id'))
        ]
        if is_temp:
            domain += [('affected', '=', True)]
        rg_result = self.env[self._name].read_group(
            domain=domain,
            groupby=['group_model_id', 'record_model_id', 'record_id'], # group per line
            fields=['siblings_ids:array_agg(id)'],
            lazy=False
        )
        mapped_siblings_ids = {
            (x['group_model_id'][0], x['record_model_id'][0], x['record_id']): x['siblings_ids']
            for x in rg_result
        }

        # check constrain per row
        for affectation in self:
            key = (affectation.group_model_id.id, affectation.record_model_id.id, affectation.record_id)
            sibling_ids = set(mapped_siblings_ids.get(key, [])) - set([affectation.id])

            if len(sibling_ids) > 0:
                raise exceptions.ValidationError(
                    _('One line cannot be affected to several columns (%s).', affectation.display_name)
                )

    #===== Quantities & M2o: constrain & compute =====#
    @api.onchange('quantity_affected')
    @api.constrains('quantity_affected')
    def _constrain_quantity(self):
        # only for groups using qties for affectation
        if self._context.get('constrain_quantity_affected_silent'):
            return
        for affectation in self:
            if not affectation.group_ref._carpentry_affectation_quantity:
                continue
            # 2024-11 - ALY: disabled to allow `qty == 0` via affectation shortcut
            # if affectation.quantity_affected <= 0:
            #     raise exceptions.ValidationError(
            #         _("Quantity affected must be strictly greater than 0, delete it instead.")
            #     )
            elif affectation.quantity_remaining_to_affect < 0:
                raise exceptions.ValidationError(
                    _("The position cannot be affected to a phase more than "
                     "its quantity on the project (%s, %s).",
                     affectation.record_ref.name, affectation.group_ref.name)
                )

    def _compute_quantity_position(self):
        for affectation in self:
            _should_compute = bool(affectation.record_ref) and 'quantity' in affectation.record_ref
            affectation.quantity_position = affectation.record_ref.quantity if _should_compute else 0
    
    @api.depends('record_id', 'quantity_affected')
    def _compute_quantity_remaining_to_affect(self):
        """ Compute remaining qty to affect of a position on *primary* affectations,
            i.e. where `record_id` is a `carpentry.position`. This is needed for
            constrain on remaining_qty>0 and good real-time display of remaining_qty
        """
        for affectation in self:
            sum_affected_siblings = 0
            if affectation.record_ref:
                sibling_ids = affectation._origin.record_ref.affectation_ids - affectation._origin
                sum_affected_siblings = sum(sibling_ids.mapped('quantity_affected'))
            
            # exclude current affectation from the sum
            affectation.quantity_remaining_to_affect = (
                affectation.quantity_position
                - sum_affected_siblings
                - affectation.quantity_affected
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

    affected = fields.Boolean(default=False) # only used when a value-field is not used, ie. for Launch, Plan, Task.Group and SaleOrder

    def _constrain_quantity(self):
        """ Neutralize this constrain in temp """
        return
