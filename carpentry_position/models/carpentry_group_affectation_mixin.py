# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command, exceptions
from odoo.osv import expression
from collections import defaultdict

class CarpentryAffectation_Mixin(models.AbstractModel):
    """ Fields & methods for Affectations.
        Methods to override are marked with `[For overwriting]`
    """
    _name = "carpentry.group.affectation.mixin"
    _description = 'Affectation Mixin'


    #===== Affectations params =====#
    # True if model is a Carpentry Group, see `carpentry.group.affectation._selection_res_model()`
    _carpentry_affectation = True
    # whether affectation uses qty fields in `carpentry.group.affectation` (e.g. for phases)
    _carpentry_affectation_quantity = False
    # whether in x2many_2d_matrix, the `client` field may be linked to several `record` fields
    _carpentry_affectation_allow_m2m = True
    # for affectation shortcut (e.g. `lot_ids` for phases, `phase_ids` for launches)
    _carpentry_affectation_section = False # # when lines are grouped (eg. positions groupped by lot for affectations of Phases)


    affectation_ids = fields.One2many(
        comodel_name='carpentry.group.affectation',
        inverse_name='group_id',
        string='Affectations',
        domain=[('group_res_model', '=', _name)], # this line must be overriten/copied with `_name` of heriting models
    )
    section_ids = fields.One2many(
        comodel_name=_name, # this line must be overriten/copied in heriting models
        string='Sections',
        domain="[('project_id', '=', project_id)]",
        compute='_compute_section_ids',
        inverse='_inverse_section_ids',
        help='With at least 1 position in commun',
    )
    sum_quantity_affected = fields.Float(
        string='Positions Count', # `Positions Count` or `Budget sum` depending the use-case
        compute='_compute_sum_quantity_affected',
        help='Sum of affected quantities'
    )
    readonly_affectation = fields.Boolean(
        # technical UI field to `readonly` either `section_ids` or `affectation_ids`,
        # because the 2 cannot be modified at same time without form saving
        # Little trick: this boolean is displayed with widget `boolean_toggle` which triggers
        # a form saving when modified by user
        string='Readonly Affectation',
        default=True,
    )
    sequence = fields.Integer() # to be defined on inheriting model

    #===== CRUD =====#
    def unlink(self):
        """ `ondelete='cascade'` does not exist on Many2oneReference fields
            of `carpentry.group.affectation` => just replay it
        """
        domain = self._get_unlink_domain()
        self.env['carpentry.group.affectation'].search(domain).unlink()
        return super().unlink()
    
    def _get_unlink_domain(self):
        return expression.OR([
            self._get_domain_affect('record'),
            self._get_domain_affect('group'),
        ])
    
    def write(self, vals):
        """ Manually update affectation's fields, because @api.depends('record_ref.any_field')
            on Reference field is not supported (see `carpentry.group.affectation`)
        """
        res = super().write(vals)

        # sequence
        if 'sequence' in vals:
            self._set_affectations_sequence(vals['sequence'])
        
        # active
        if any(x not in vals for x in ['active', 'state']):
            self._set_affectations_active()
        
        return res

    def _set_affectations_sequence(self, group_sequence):
        """ Two types of affectation's sequence must be updated:
            1. ones where `self.sequence` is `seq_group` -> self.affectation_ids
            2. ones where `self.sequence` is `seq_section` -> trickier
        """
        # (pre-2). Get affectations where `self.sequence` is `seq_section`
        domain = self._get_domain_affect(group='section')
        mapped_affectation_ids_section = {
            affectation.section_id: affectation
            for affectation in self.env['carpentry.group.affectation'].search(domain)
        }

        # 1 & 2. Update `seq_group` and `seq_section`
        for group in self:
            group.affectation_ids.seq_group = group_sequence
            affectation_ids_section = mapped_affectation_ids_section.get(group.id)
            if affectation_ids_section:
                affectation_ids_section.seq_section = group_sequence
    
    def _set_affectations_active(self):
        """ Actualize `active` field of affectations

            Example: a PO reserves budget on launches *A* and *B*. One archives launch *A*.
             One should not see archived launch *A* on PO's affectations.
        """
        self = self.with_context(active_test=False)
        for group in self:
            for a in group.affectation_ids:
                a.active = group._get_affectation_active(a.record_ref, a.group_ref, a.section_ref)
    
    def _get_affectation_active(self, *args):
        """ Calculate `affectation.active` from `record_ref`, `group_ref` and/or `section_ref`
             optionally passed in `*args`, depending their fields `active` and possibly `state`:
             - `active`: if 1 arg is archived   => archive the affectation
             - `state`:  if 1 arg is ['cancel'] => archive the affectation

             (!) for budget, the `section_ref` state is ignored
        """
        active = True
        for arg in args:
            if not arg:
                continue
            # active
            if hasattr(arg, 'active'):
                active = active and arg['active']
            # state
            if hasattr(arg, 'state'):
                active = active and arg['state'] not in ['cancel']
        return active

    
    #====== Affectation Temp ======#
    # -- Generic methods to be / that can be overritten, for compute and/or inverse of `affectation.temp` --
    def _get_record_refs(self):
        """ [*Must* be overritten]
            :return: recordset of matrix' lines (`record_id`), e.g.:
            - for Phases: project's positions
            - for Launches: phases' affectations
            - for Purchase Order: analytic account of PO lines' analytic distributions
        """
        self.ensure_one()

    def _get_mapped_records_per_groups(self, record_refs, group_refs):
        """ Called when generating 2d vals_list, allowing to filter
            `record_refs` (e.g. launchs) as per a `group_ref` (e.g. analytic)
            :return: {group_ref.id: record_refs}
                if group_ref is not found, the column will contain all record_refs
        """
        return {}

    def _get_affect_vals(self, mapped_model_ids, record_ref, group_ref, affectation=False):
        """ Generates 1 cell's vals of `affectation` or `affectation.temp`
            Used in both way (compute `temp` and inverse to *real*)
            Args:
            - `record_ref` (line): 1 record of:
                > Position or Affectation (for position affectation)
                > Launch or Project (for budget reservation)
            - `group_ref` (column): 1 record of:
                > a Carpentry Group like Phase or Launch (for position affectation)
                > or Analytic (for budget reservation)
            - `affectation`:
                * if inverse (temp->real): record of `temp`
                * if compute (real->team): **False** or record of *real*
                * if new affectation (shortcut): False
        """
        record_ref = affectation.record_ref if affectation else record_ref
        group_ref = affectation.group_ref if affectation else group_ref
        section_ref = record_ref.group_ref if self._carpentry_affectation_section else False

        # vals
        qty = affectation.quantity_affected if affectation else self._default_quantity(record_ref, group_ref)
        active = affectation.active if affectation else self._get_affectation_active(record_ref, group_ref, section_ref)

        vals = {
            'project_id': record_ref.id if record_ref._name == 'project.project' else record_ref.project_id.id,
            # M2o models
            'record_model_id': mapped_model_ids.get(record_ref._name),
            'group_model_id': affectation.group_model_id.id if affectation else mapped_model_ids.get(group_ref._name),
            'section_model_id': bool(section_ref) and mapped_model_ids.get(section_ref._name),
            # M2o ids
            'group_id': group_ref.id,
            'record_id': record_ref.id,
            'section_id': bool(section_ref) and section_ref.id,
            # sequence
            'sequence': record_ref.sequence, # sec_record
            'seq_group': 'sequence' in group_ref and group_ref.sequence, # no sequence for PO
            'seq_section': bool(section_ref) and section_ref.sequence,
            # vals
            'quantity_affected': qty,
            'active': active
        }
        return vals
    
    def _default_quantity(self, record_ref, group_ref):
        # other possibility for phase: `affectation.quantity_remaining_to_affect`
        return 0.0

    def _get_mapped_model_ids(self):
        """ Needed outside of `_get_affect_vals()` for performance """
        model_ids = self.env['ir.model'].sudo().search([])
        return {x.model: x.id for x in model_ids}
    
    @api.model
    def _should_inverse(self, vals):
        """ [Can be overritten]
            Function to filter which records to convert from *temp* to *real* affectation
        """
        return (
            vals.get('quantity_affected') > 0 if self._carpentry_affectation_quantity
            else vals.get('affected')
        )

    def _get_domain_affect(self, group='group', group2_ids=None, group2='record'):
        """ Return domain for search on `carpentry.group.affectation[.temp]`
            :arg self: recordset of `[field]_ids`, like `group_ids`, `section_ids`, ...
        """
        domain = [(group + '_res_model', '=', self._name), (group + '_id', 'in', self.ids)]
        if group2_ids:
            domain += [(group2 + '_res_model', '=', group2_ids._name), (group2 + '_id', 'in', group2_ids.ids)]
        return domain
    

    # -- Refresh *real* `affectation` (for PO and WO) --
    def _get_affectation_ids(self, vals_list=[]):
        """ Called from PO or MO to refresh *real* affectations """
        return self._get_affectation_ids_temp(temp=False, vals_list=vals_list)
    
    def _has_real_affectation_matrix_changed(self, vals_list):
        """ When refreshing *real* affectations of PO or MO, tells if budget matrix'
            rows and cols are actually changing or if it's just an 'idle' refresh
        """
        # Get new cols & rows, as per budget matrix vals
        record_ids, group_ids = set(), set()
        for vals in vals_list:
            record_ids.add(vals['record_id'])
            group_ids.add(vals['group_id'])
        
        # Compare to existing
        return (
            record_ids != set(self.affectation_ids.mapped('record_id')) or
            group_ids != set(self.affectation_ids.mapped('group_id'))
        )
    
    def _clean_real_affectations(self, group_refs, record_refs):
        """ When unselecting `analytics` or `launches`, real affectation
            still exists but are not wished in target matrix => unlink() them
        """
        self = self.with_context(active_test=False)
        groups_ids = set(self.affectation_ids.mapped('group_id')) - set(group_refs.ids)
        record_ids = set(self.affectation_ids.mapped('record_id')) - set(record_refs.ids)
        
        affectations = self.affectation_ids.filtered(lambda x:
            # of the document (e.g. purchase order)
            x.section_res_model == self._name and x.section_id == self._origin.id and
            # from a record or group that has been unselected (launch or analytic)
            (x.group_id in groups_ids or x.record_id in record_ids)
        )
        affectations.unlink()
    
    # -- Compute of `affectation.temp` from `real` --
    def _get_affectation_ids_temp(self, temp=True, vals_list=[]):
        """ Called from a Carpentry Form (e.g. Project for Phases and Launches)
            
            :arg `self`: is a recordset of a Carpentry Group (Phases, Launches, ...)
            :return: Command object list for One2many field of `carpentry.group.affectation.temp`
        """
        self = self.with_context(active_test=False) # browse even in archived affectations

        # for PO and WO
        if vals_list and len(self) == 1:
            affectation_temp_ids_ = self._write_or_create_affectations(vals_list, temp).ids
        # for Phases and Launches
        else:
            affectation_temp_ids_ = []
            for group in self:
                vals_list = group._get_affectation_ids_vals_list(temp)
                affectation_temp_ids_ += group._write_or_create_affectations(vals_list, temp).ids
        return [Command.set(affectation_temp_ids_)]

    #===== Affectation method =====#
    def _get_affectation_ids_vals_list(self, temp, record_refs=None, group_refs=None):
        """ Useful to either:
            - fully compute `temp` affectation from real + fill in cells gaps (e.g. phase & launch)
            - refresh *real* affectations and add a new column or row (e.g. purchase)
        """
        self = self.with_context(active_test=False)
        self.ensure_one()

        # Get target values
        mapped_model_ids = self._get_mapped_model_ids()
        record_refs = record_refs or self._get_record_refs()
        group_refs = group_refs or self._get_group_refs()
        if not temp:
            # Remove affectations of unselected rows or cols
            self._clean_real_affectations(group_refs, record_refs)

        # Generate new x2m_2d_matrix
        mapped_records_per_groups = self._get_mapped_records_per_groups(record_refs, group_refs)
        mapped_real_ids = self._get_mapped_real_ids()
        vals_list = []
        for group_ref in group_refs:
            record_refs_filtered = mapped_records_per_groups.get(group_ref.id, record_refs)
            for record_ref in record_refs_filtered:
                vals = self._add_matrix_cell(group_ref, record_ref, mapped_real_ids, mapped_model_ids, temp)
                vals_list.append(vals)
        return vals_list
    
    def _add_matrix_cell(self, group_ref, record_ref, mapped_real_ids, mapped_model_ids, temp):
        self = self.with_context(active_test=False)

        key = (mapped_model_ids.get(group_ref._name), group_ref.id, record_ref.id)
        affectation = mapped_real_ids.get(key)

        vals = self._get_affect_vals(mapped_model_ids, record_ref, group_ref, affectation)
        affected = {'affected': bool(affectation)} if temp else {}
        return vals | affected

    def _get_mapped_real_ids(self):
        self = self.with_context(active_test=False)

        return {
            (affectation.group_model_id.id, affectation.group_id, affectation.record_id): affectation
            for affectation in self.affectation_ids
        }

    def _get_group_refs(self):
        """ `group` is either the Carpentry Group (Phase, Launch)
            or Analytic (for PO, MO, ...)
        """
        return self.with_context(active_test=False)
    
    def _write_or_create_affectations(self, vals_list, temp):
        """ Returns the affectation_ids that can be used in Command.set() for a O2m on a `form`,
            by searching any existing records in database (and updating them with val_list) or creating them
        """
        self = self.with_context(active_test=False)

        model = 'carpentry.group.affectation'
        if temp:
            model += '.temp'
        affectation_ids = self.env[model].search(self._get_domain_affect())
        
        vals_list_create = []
        for vals in vals_list:
            domain_cell = self._get_domain_write_or_create(vals)
            existing_id = affectation_ids.filtered_domain(domain_cell)
            if existing_id.ids:
                existing_id.write(vals)
            else:
                vals_list_create.append(vals)
        res = affectation_ids | affectation_ids.create(vals_list_create)
        return res

    def _get_domain_write_or_create(self, vals):
        """ Over-writtable for budget, to add `section_id`
            But we don't want `section_id` for position-to-phase/launch
        """
        return [
            ('record_id', '=', vals.get('record_id')),
            ('group_id', '=', vals.get('group_id')),
        ]
    
    # -- Inverse of `affectation.temp` to `real` --
    @api.model
    def _inverse_affectation_ids_temp(self, vals_list):
        """ Called from form's `write()`
            Write or create records in `carpentry.group.affectation` from `carpentry.group.affectation.temp`
            Delete the other records, ie. ones in `carpentry.group.affectation` not written or created
            (ie. disabled in temp)

            Args:
            * `self`: recordset of Carpentry Group
            * `vals_list`: {temp_id: vals} of **updated only** `affectation_ids_temp`
                where `vals` **only** keys are updated vals (i.e. `quantity_affected` or `affected`)
        """
        self = self.with_context(
            constrain_quantity_affected_silent=True,
            active_test=False
        )
        vals_list_create, ids_to_remove = [], []

        # *temp* affectations (user input sent to `write()`)
        affectation_ids_temp = self.env['carpentry.group.affectation.temp'].browse(set(vals_list.keys()))
        # *real* affectation_ids (database data before user input sent to `write()`)
        mapped_affectation_ids = {
            (affectation.group_id, affectation.record_id): affectation
            for affectation in self.affectation_ids
        }

        mapped_model_ids = self._get_mapped_model_ids()
        real_ids = self.env['carpentry.group.affectation']
        for temp in affectation_ids_temp:
            real = mapped_affectation_ids.get((temp.group_id, temp.record_id))
            user_vals = vals_list.get(temp.id, {})

            # to remove
            if not self._should_inverse(user_vals):
                if real:
                    ids_to_remove.append(real.id)
            else:
                # filter fields that can't be written in `carpentry.group.affectation` (real) like `affected`
                user_vals = {
                    key: value for key, value in user_vals.items()
                    if key in self.env['carpentry.group.affectation']
                }
                # to save (write or create)
                if real:
                    real_ids |= real
                    real.write(user_vals)
                else:
                    # Only user input is in `vals`. To create a valid *real* affectation
                    # `vals` must be completed with values from database
                    real_vals = self._get_affect_vals(mapped_model_ids, temp.record_ref, temp.group_ref, temp)
                    vals_list_create.append(real_vals | user_vals)

        # apply to changes in `carpentry.group.affectation` (real)
        real_ids |= self.env['carpentry.group.affectation'].create(vals_list_create)
        self.affectation_ids.browse(ids_to_remove).unlink()

        # check constrain once all CRUD is done, else constrain is mis-computed
        real_ids.with_context(constrain_quantity_affected_silent=False)._constrain_quantity()
    
    
    #===== Affectation shortcut =====#
    @api.depends('affectation_ids')
    def _compute_section_ids(self):
        """ 'section_ids' are parent/related groups having at least 1 position in commun with the group
            e.g.: for phases, they are `lot_ids`, for launches they are `phase_ids`
        """
        if not self._carpentry_affectation_section:
            return
        for group in self:
            section_ids_ = [x.record_ref.group_ref.id for x in group._origin.affectation_ids]
            group.section_ids = [Command.set(set(section_ids_))]

    def _inverse_section_ids(self):
        """ Pre-fill 'affectation_ids' according to sections, e.g.:
            - prefill Phases'   affectations copying Lot's   ones
            - prefill Launches' affectations copying Phases' ones
        """
        if not self._carpentry_affectation_section:
            return
        
        mapped_model_ids = self._get_mapped_model_ids()
        for group in self:
            # 1. Unlink affectations of removed sections
            group.affectation_ids.filtered(lambda x: (
                x.record_ref.group_ref.id not in group.section_ids.ids
            )).unlink()

            # 2. Add affectations of added sections
            # 2a. Get new sections *only*, i.e. sections (e.g. phases) not already
            #     partially linked with the current group (e.g. a launch)
            new_section_ids = group._origin.section_ids
            # remove from `new_section_ids` the already linked sections
            for x in group._origin.affectation_ids:
                new_section_ids -= x.record_ref.group_ref

            # 2b. Of these new sections, get their remaining available affectations
            section_affectations = group._get_remaining_affectations_from_sections(new_section_ids)

            # 3. Add new affectations
            group._add_affectations_from_sections(section_affectations, mapped_model_ids)

    def refresh_from_sections(self):
        """ Button to allow refreshing affectations from linked sections.
            This is useful if section's affectations changes **after** the group affectations
        """
        if not self._carpentry_affectation_section:
            return
        
        mapped_model_ids = self._get_mapped_model_ids()
        for group in self:
            # 1. Of current sections, get their positions (for lots) or affectations (for phases)
            #    still affectable (qty_remaining > 0 or not affected) and not already present in the group
            current_record_ids = group.affectation_ids.mapped('record_id')
            section_affectations = (
                group._get_remaining_affectations_from_sections(group._origin.section_ids)
                .filtered(lambda x: x.id not in current_record_ids)
            )

            # 2. Add them to group's affectations
            group._add_affectations_from_sections(section_affectations, mapped_model_ids)

    def _get_remaining_affectations_from_sections(self, sections):
        """ For given `sections`, return positions (for lots) or affectations (for phases)
            with remaining quantity to affect, i.e.:
             * quantity_remaining_to_affect > 0 (qty), or
             * not already affected (bool)
        """
        _filter = lambda x: True
        if self._carpentry_affectation_quantity: # eg. phases
            # affectations with remaining qty to affect
            _filter = lambda affectation: affectation.quantity_remaining_to_affect > 0
        elif not self._carpentry_affectation_allow_m2m:
            # affectations not already affected to another group
            _filter = lambda affectation: not affectation.affectation_ids.ids
        return sections.affectation_ids.filtered(_filter)
    
    def _add_affectations_from_sections(self, section_affectations, mapped_model_ids):
        """ 1. Convert section's affectations to group's affectation vals_list
            2. Write them in group's `affectation_ids`
        """
        self.ensure_one()
        vals_list = [
            self._get_affect_vals(mapped_model_ids, record_ref=affectation, group_ref=self)
            for affectation in section_affectations
        ]
        self.affectation_ids = [Command.create(vals) for vals in vals_list]
    
    #====== Buttons for Affectation shortcuts ======#
    def create_groups_from_sections(self):
        """ Create a kind of group (e.g. phase or launch)
            from its section (e.g. lots or phases)

            The section's model Class must define `_carpentry_affectation_section_of` attr

            :return: Redirect to create groups (tree view)
        """
        Group = self.env['carpentry.group.' + self._carpentry_affectation_section_of]
        groups = Group.create([
            section._get_group_vals_from_section()
            for section in self
        ])

        action = {
            'type': 'ir.actions.act_window',
            'res_model': Group._name,
            'name': _(Group._description),
            'view_mode': 'tree',
            'domain': [('id', 'in', groups.ids)]
        }
        return action
    
    def _get_group_vals_from_section(self):
        """ :arg:    `self` is the section
            :return: group's vals
        """
        self.ensure_one()
        return {
            'name': self.name,
            'project_id': self.project_id.id,
            'section_ids': [Command.set([self.id])]
        }

    #====== Affectations counters ======#
    @api.depends('affectation_ids')
    def _compute_sum_quantity_affected(self):
        """ Sums of 'quantity_affected' in 'carpentry.group.affectation' """
        rg_result = self.env['carpentry.group.affectation'].read_group(
            domain=[('group_res_model', '=', self._name), ('group_id', 'in', self.ids)],
            fields=['quantity_affected:sum'],
            groupby=['group_id'],
        )
        mapped_data = {x['group_id']: x['quantity_affected'] for x in rg_result}
        for record in self:
            record.sum_quantity_affected = mapped_data.get(record.id, 0)

    #===== Button =====#
    def button_group_quick_create(self):
        project_id_ = self._get_project_id(raise_if_not_found=True)
        project = self.env['project.project'].browse(project_id_)
        section_ids = project[self._carpentry_affectation_section + '_ids']
        return section_ids.create_groups_from_sections()
    

    def toggle_readonly_affectation(self):
        """ If there is no affectation: stick to preparation of affectations (left)
            Else, toggle between the 2 state
        """
        if not self.affectation_ids and self.readonly_affectation:
            self._raise_if_no_affectations()
        self.readonly_affectation = not self.readonly_affectation
    
    def _raise_if_no_affectations(self):
        raise exceptions.UserError(_(
            'There is no position to affect from these lots or these phases.'
        ))


    def button_open_affectation_matrix(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'res_id': self._get_project_id(raise_if_not_found=True),
            'view_mode': 'form',
            'view_id': self.env.ref('carpentry_position.carpentry_group_affectation_temp_matrix').id,
            'context': self._context | {'res_model': self._name}
        }
