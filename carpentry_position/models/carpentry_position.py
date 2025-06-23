# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from collections import defaultdict

class Position(models.Model):
    _name = "carpentry.position"
    _description = "Position"
    _inherit = ['carpentry.group.mixin']
    _order = "seq_group, lot_id, sequence"
    _rec_name = "display_name"
    _rec_names_search = ['name']

    #===== Fields methods =====#
    @api.depends('name')
    def _compute_display_name(self):
        for position in self:
            position.display_name = position._get_display_name()
    def _get_display_name(self, display_with_suffix=False):
        """ We need to tweak positions' `display_name` when called in a x2many_2d_matrix """
        self.ensure_one()
        display_with_suffix = self._context.get('display_with_suffix', display_with_suffix)

        prefix, suffix = '', ''
        if display_with_suffix:
            prefix = "[%s] " % (self.lot_id.name or '')
            suffix = " (%s)" % (self.quantity)
        return prefix + self.name + suffix
    
    #===== Fields =====#
    lot_id = fields.Many2one('carpentry.group.lot',
        domain="[('project_id', '=', project_id)]",
        ondelete='set null'
    )
    quantity = fields.Integer(
        string='Quantity',
        required=True
    )
    surface = fields.Float(
        string='Surface',
        digits=(6,2)
    )
    range = fields.Char(
        string='Range'
    )
    description = fields.Char(
        string='Description'
    )

    quantity_remaining_to_affect = fields.Integer(
        string='Remaining', 
        compute='_compute_quantities_and_state', 
        compute_sudo=True,
        help='Quantity remaining for affection in phases',
    )
    state = fields.Selection(
        selection=[
            ('na', 'n/a'),
            ('none', 'None'),
            ('warning_phase', 'Partial on phase(s)'),
            ('warning_launch', 'Partial on launch(es)'),
            ('done', 'OK')
        ],
        string='Affectation status',
        default='na',
        compute='_compute_quantities_and_state',
        store=True,
        compute_sudo=True,
        help='Indicates whether quantity is fully affected or not in phases and launches',
    )

    # tricks to fit with `carpentry.group.affectation.mixin` field names and logics (see `_get_affect_vals()`)
    group_ref = fields.Many2one(
        related='lot_id',
        string='Group Ref'
    )
    seq_group = fields.Integer(
        related='lot_id.sequence',
        string='Lot Sequence',
        store=True,
    )
    affectation_ids = fields.One2many(
        comodel_name='carpentry.group.affectation',
        inverse_name='record_id',
        string='Affectations',
        domain=[('record_res_model', '=', _name)]
    )

    _sql_constraints = [('name_per_project', 'check(1=1)', ''),]

    #===== Constrain =====#
    @api.constrains('quantity')
    def _constrain_quantity(self):
        """ Cannot lower quantity under affected qty in phases """
        # because `carpentry_group_affectation.quantity_available` is computed not store,
        # affectation's constrain is not called when changing parent position's quantity
        # => just call the existing constrain explicitely when changing position's qty
        self.affectation_ids._constrain_quantity()
    
    #===== CRUD =====#
    @api.onchange('sequence')
    def _onchange_sequence(self):
        """ Manually update affectation's sequences *and children sequences* """
        # Retrieve all affectations and children affectations of these positions
        # (e.g. launches affectations from phases' ones)
        mapped_affectation_ids = {x.record_id: [x] for x in self.affectation_ids}
        children_affectation_ids = self.affectation_ids.affectation_ids
        while children_affectation_ids.ids:
            for x in children_affectation_ids:
                mapped_affectation_ids[x.position_id].append(x)
            children_affectation_ids = children_affectation_ids.affectation_ids
        
        # Update `sequence`
        for position in self:
            affectation_ids = mapped_affectation_ids.get(position.id)
            if affectation_ids:
                affectation_ids.sequence = position.sequence

    # Clean lots with no positions
    def _clean_lots(self):
        """ Remove lots not linked to any positions """
        domain = [('id', 'in', self.lot_id.ids), ('affectation_ids', '=', False)]
        orphan_lots = self.env['carpentry.group.lot'].search(domain)
        orphan_lots.unlink()
    
    # Cf. unlink() of carpentry_group_affectation_mixin.py => need to CASCADE the unlink to the affectations
    def _clean_affectations(self):
        Affectation = self.env['carpentry.group.affectation']
        
        # delete before the position its affectations with phases
        phase_domain = self._get_domain_affect('record')
        phase_affectations = Affectation.search(phase_domain)
        
        # ...but even 1st delete position-to-launch affectation that could be empty
        empty_affectations = phase_affectations.filtered(lambda x: x.quantity_affected == 0.0)
        domain_launch = [
            ('record_res_model', '=', Affectation._name),
            ('record_id', 'in', empty_affectations.ids),
        ]
        launch_affectations = Affectation.search(domain_launch)
        
        launch_affectations.unlink()
        phase_affectations.unlink()
    
    def unlink(self):
        self._clean_lots()
        self._clean_affectations()
        return super().unlink()
    
    def write(self, vals):
        if 'lot_id' in vals:
            self._clean_lots()
        return super().write(vals)
    
    #===== Compute =====#
    @api.depends('quantity', 'project_id.affectation_ids_project.quantity_affected')
    def _compute_quantities_and_state(self):
        # Helper dict `mapped_models`
        domain = [('model', 'in', ['carpentry.group.phase', 'carpentry.group.launch'])]
        mapped_models = {
            x['id']: x['model']
            for x in self.env['ir.model'].sudo().search_read(domain)
        }

        # For a given position, get its quantity already affected in phases and launches
        rg_result = self.env['carpentry.group.affectation'].read_group(
            domain=[('position_id', 'in', self.ids)],
            groupby=['position_id', 'group_model_id'],
            fields=['quantity_affected:sum'],
            lazy=False,
        )
        sum_affected = defaultdict(dict)
        for data in rg_result:
            model = mapped_models[data['group_model_id'][0]].replace('carpentry.group.', '')
            sum_affected[model][data['position_id'][0]] = data['quantity_affected']
        
        # update fields
        for position in self:
            position.quantity_remaining_to_affect = position.quantity - sum_affected['phase'].get(position.id, 0)
            
            state = 'done'
            if position.quantity == 0:
                state = 'na'
            elif position.quantity_remaining_to_affect == position.quantity:
                state = 'none'
            elif position.quantity_remaining_to_affect > 0:
                state = 'warning_phase'
            elif position.quantity > sum_affected['launch'].get(position.id, 0):
                state = 'warning_launch'
            position.state = state

    #===== Button =====#
    def copy(self, default=None):
        return super().copy((default or {}) | {
            'name': self.name + _(' (copied)')
        })
