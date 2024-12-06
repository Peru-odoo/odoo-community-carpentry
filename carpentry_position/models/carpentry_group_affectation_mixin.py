# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command
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
        string='Positions Affectations',
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
    sum_position_quantity_affected = fields.Integer(
        string='Positions Count',
        compute='_compute_sum_position_quantity_affected',
        help='Sum of affected quantities',
        store=True
    )
    readonly_affectation = fields.Boolean(
        # technical UI field to `readonly` either `section_ids` or `affectation_ids`,
        # because the 2 cannot be modified at same time without form saving
        # Little trick: this boolean is displayed with widget `boolean_toggle` which triggers
        # a form saving when modified by user
        string='Readonly Affectation',
        default=True,
    )

    #===== CRUD =====#
    def unlink(self):
        """ `ondelete='cascade'` does not exist on Many2oneReference fields
            of `carpentry.group.affectation` => just replay it
        """
        self.env['carpentry.group.affectation'].search(self._get_domain_affect()).unlink()
        return super().unlink()


    @api.onchange('sequence')
    def _onchange_sequence(self):
        print('_onchange_sequence')
        """ Manually update affectation's sequences, because @api.depense('record_ref.sequence')
            on Reference field is not supported (see `carpentry.group.affectation`)

            Two types of affectation's sequence must be updated:
            1. ones where `self.sequence` is `seq_group` -> self.affectation_ids
            2. ones where `self.sequence` is `seq_section` -> trickier
        """
        # 2. Get affectations where `self.sequence` is `seq_section`
        domain = self._get_domain_affect(group='section')
        mapped_affectation_ids_section = {
            affectation.section_id: affectation
            for affectation in self.env['carpentry.group.affectation'].search(domain)
        }

        # Update `seq_group` and `seq_section`
        for group in self:
            group.affectation_ids.seq_group = group.sequence
            affectation_ids_section = mapped_affectation_ids_section.get(group.id)
            if affectation_ids_section:
                affectation_ids_section.seq_section = group.sequence

    #====== Affectation Temp ======#
    # -- Generic methods to be / that can be overritten, for compute and/or inverse of `affectation.temp` --
    def _get_compute_record_refs(self):
        """ [*Must* be overritten]
            :return: recordset of matrix' lines (`record_id`), e.g.:
            - for Phases: project's positions
            - for Launches: phases' affectations
        """
        print('_get_compute_record_refs')
        self.ensure_one()
    
    def _get_affect_vals(self, mapped_model_ids, record_ref, affectation=False):
        """ Generates 1 cell's vals of `affectation` or `affectation.temp`
            Used in both way (compute `temp` and inverse to *real*)
            Args:
            - `self` (grouping_id, column): 1 record of a Carpentry Group (Phase, Launch)
            - `record_ref` (line): 1 record of Position or Affectation
            - `affectation`:
                * if inverse (temp->real): record of `temp`
                * if compute (real->team): **False** or record of *real*
                * if new affectation (shortcut): False
        """
        print('_get_affect_vals')
        self.ensure_one()
        group_ref = affectation.group_ref if affectation else self
        record_ref = affectation.record_ref if affectation else record_ref
        section = self._carpentry_affectation_section

        vals = {
            'project_id': group_ref.project_id.id,
            # M2o models
            'group_model_id': affectation.group_model_id.id if affectation else mapped_model_ids.get(self._name),
            'record_model_id': mapped_model_ids.get(record_ref._name),
            'section_model_id': mapped_model_ids.get(record_ref.group_ref._name) if section else False,
            # M2o ids
            'group_id': group_ref.id,
            'record_id': record_ref.id,
            'section_id': record_ref.group_ref.id if section else False,
            # sequence
            'sequence': record_ref.sequence, # sec_record
            'seq_group': group_ref.sequence,
            'seq_section': record_ref.seq_group if section else 0,
            # vals
            'quantity_affected': (
                int(bool(affectation) and affectation.quantity_affected)
                if group_ref._carpentry_affectation_quantity else False
            ),
        }
        print('_get_affect_vals')
        return vals
    
    def _get_mapped_model_ids(self):
        """ Needed outside of `_get_affect_vals()` for performance """
        print('_get_mapped_model_ids:start')
        model_ids = self.env['ir.model'].sudo().search([])
        print('_get_mapped_model_ids:end')
        return {x.model: x.id for x in model_ids}
    
    @api.model
    def _should_inverse(self, vals):
        """ [Can be overritten]
            Function to filter which records to convert from *temp* to *real* affectation
        """
        print('_should_inverse')
        return (
            vals.get('quantity_affected') > 0 if self._carpentry_affectation_quantity
            else vals.get('affected')
        )


    # -- Compute of `affectation.temp` from `real` --
    @api.depends('affectation_ids')
    def _compute_affectation_ids_temp(self, vals_list=None):
        """ Called from a Carpentry Form (e.g. Project for Phases and Launch)
            :return: Command object list for One2many field of `carpentry.group.affectation.temp`
            `self` is a recordset of a Carpentry Group (Phases, Launches, ...)
        """
        print('_compute_affectation_ids_temp start')
        vals_list = vals_list or self._get_affectation_ids_temp_vals_list()
        matrix = self._write_or_create_temp(vals_list)
        print('_compute_affectation_ids_temp end')
        return [Command.set(matrix.ids)]
    
    def _get_affectation_ids_temp_vals_list(self):
        # Get real values to put in new `temp_ids`
        print('_get_affectation_ids_temp_vals_list start')
        mapped_real_ids = {
            (affectation.group_id, affectation.record_id): affectation
            for affectation in self.affectation_ids
        }

        mapped_model_ids = self._get_mapped_model_ids()

        # Generate new x2m_2d_matrix of `temp_ids`
        record_refs = self._get_compute_record_refs()
        vals_list = []
        for group_ref in self:
            for record_ref in record_refs:
                affectation = mapped_real_ids.get((group_ref.id, record_ref.id))
                vals = group_ref._get_affect_vals(mapped_model_ids, record_ref, affectation)
                vals_list.append(vals | {'affected': bool(affectation)})
        print('_get_affectation_ids_temp_vals_list end')
        return vals_list
    
    def _write_or_create_temp(self, vals_list):
        """ Returns the affectation_temp_ids that can be used in Command.set() for a O2m on a `form`,
            by searching any existing records in database (and updating them with val_list) or creating them
        """
        print('_write_or_create_temp start')
        temp_ids = self.env['carpentry.group.affectation.temp'].search(self._get_domain_affect())
        vals_list_create_temp = []
        for vals in vals_list:
            domain_cell = [
                ('record_id', '=', vals.get('record_id')),
                ('group_id', '=', vals.get('group_id'))
            ]
            existing_id = temp_ids.filtered_domain(domain_cell)
            if existing_id.ids:
                existing_id.write(vals)
            else:
                vals_list_create_temp.append(vals)
        print('_write_or_create_temp end')
        return temp_ids | temp_ids.create(vals_list_create_temp)
    
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
        print('_inverse_affectation_ids_temp start')
        self = self.with_context(constrain_quantity_affected_silent=True)
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
                    real_vals = temp.group_ref._get_affect_vals(mapped_model_ids, temp.record_ref, temp)
                    vals_list_create.append(real_vals | user_vals)

        # apply to changes in `carpentry.group.affectation` (real)
        real_ids |= self.env['carpentry.group.affectation'].create(vals_list_create)
        self.affectation_ids.browse(ids_to_remove).unlink()

        # check constrain once all CRUD is done, else constrain is mis-computed
        real_ids.with_context(constrain_quantity_affected_silent=False)._constrain_quantity()
        print('_inverse_affectation_ids_temp end')
    
    
    #===== Affectation shortcut =====#
    @api.depends('affectation_ids')
    def _compute_section_ids(self):
        """ 'section_ids' are parent/related groups having at least 1 position in commun with the group
            e.g.: for phases, they are `lot_ids`, for launches they are `phase_ids`
        """
        if not self._carpentry_affectation_section:
            return
        for group in self:
            section_ids_ = [x.record_ref.group_ref.id for x in group.affectation_ids]
            group.section_ids = [Command.set(set(section_ids_))]

    def _inverse_section_ids(self):
        """ Pre-fill 'affectation_ids' according to sections, e.g.:
            - prefill Paunches' affectations copying Lot's ones
            - prefill Launches' affectations copying Phases' ones
        """
        if not self._carpentry_affectation_section:
            return
        print('_inverse_section_ids start')
        
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

            # 2b. Of these new sections, filter to their remaining available affectations,
            #     i.e. quantity_remaining_to_affect > 0 (qty) or not already affected (bool)
            _filter = lambda x: True
            if group._carpentry_affectation_quantity: # eg. phases
                # affectations with remaining qty to affect
                _filter = lambda affectation: affectation.quantity_remaining_to_affect > 0
            elif not group._carpentry_affectation_allow_m2m:
                # affectations not already affected to another group
                _filter = lambda affectation: not affectation.affectation_ids.ids
            new_affectation_ids = new_section_ids.affectation_ids.filtered(_filter)

            # prepare vals & write
            vals_list = [
                (
                    group._get_affect_vals(mapped_model_ids, record_ref=affectation)
                    | {'quantity_affected': 0} # other possibility: `affectation.quantity_remaining_to_affect`
                ) for affectation in new_affectation_ids
            ]
            group.affectation_ids = [Command.create(vals) for vals in vals_list]
        print('_inverse_section_ids end')

    #====== Buttons for Affectation shortcuts ======#
    def _populate_group_from_section(self):
        """ Populate a kind of group (e.g. phase or launch)
            from its section (e.g. lots or phases)
        """
        print('_populate_group_from_section start')
        project_id_ = self._get_project_id(raise_if_not_found=True)
        section_field = self._carpentry_affectation_section

        section_ids = self.env['project.project'].browse(project_id_)[section_field + '_ids']
        self.create([{
            'name': section.name,
            'project_id': project_id_,
            'section_ids': [Command.set(section.ids)]
        } for section in section_ids])
        print('_populate_group_from_section end')


    #====== Affectations counters ======#
    @api.depends('affectation_ids')
    def _compute_sum_position_quantity_affected(self):
        """ Sums of 'quantity_affected' in 'carpentry.group.affectation',
            eg. for a phase or a launch
        """
        print('_compute_sum_position_quantity_affected start')
        # Get and group mapped data by `group_id`
        mapped_data = defaultdict(int)
        for key, qty in self._get_quantities().items():
            mapped_data[dict(key)['group_id']] += qty
        
        # Set sum or 0
        for record in self:
            record.sum_position_quantity_affected = mapped_data.get(record.id, 0)
        print('_compute_sum_position_quantity_affected end')

    def _get_quantities(self):
        """ :return: param of `carpentry_position_budget.sum()` """
        quantities = defaultdict(int)
        print('_get_quantities start')
        
        for affectation in self.affectation_ids:
            # handle nested affectation to find related `position_id` of this affectation
            position_id, nested = affectation.record_ref, False
            while position_id._name != 'carpentry.position':
                position_id = position_id.record_ref
                nested = True
            
            # sum position's affected qty to the group
            key = frozenset({
                'group_id': affectation.group_id,
                'position_id': position_id.id
            }.items())

            field_qty = 'quantity_affected_parent' if nested else 'quantity_affected'
            quantities[key] += affectation[field_qty]
        
        print('_get_quantities end')
        return quantities


    #===== Button =====#
    def button_group_quick_create(self):
        self._populate_group_from_section()
    
    def toggle_readonly_affectation(self):
        self.readonly_affectation = not self.readonly_affectation

    def button_open_affectation_matrix(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'res_id': self._get_project_id(raise_if_not_found=True),
            'view_mode': 'form',
            'view_id': self.env.ref('carpentry_position.carpentry_group_affectation_temp_matrix').id,
            'context': self._context | {
                'res_model': self._name
            }
        }
