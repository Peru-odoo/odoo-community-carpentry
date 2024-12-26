# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.osv import expression

from collections import defaultdict
import datetime

class Project(models.Model):
    _inherit = ["project.project"]

    #===== Fields =====#
    # positions, phases, launch
    position_ids = fields.One2many(
        'carpentry.position',
        'project_id',
        string='Positions'
    )
    position_count = fields.Integer(
        string='Positions Count',
        compute='_compute_position_count',
        store=True
    )
    lot_ids = fields.One2many(
        'carpentry.group.lot',
        'project_id',
        string='Lots'
    )
    phase_ids = fields.One2many(
        'carpentry.group.phase',
        'project_id',
        string='Phases'
    )
    launch_ids = fields.One2many(
        'carpentry.group.launch',
        'project_id',
        string='Launches'
    )

    # affectations
    affectation_ids = fields.One2many(
        'carpentry.group.affectation',
        'project_id',
        string='Affectations'
    )
    affectation_ids_temp_phase = fields.One2many(
        'carpentry.group.affectation.temp',
        readonly=False,
        compute='_compute_affectation_ids_temp_phase'
    )
    affectation_ids_temp_launch = fields.One2many(
        'carpentry.group.affectation.temp',
        readonly=False,
        compute='_compute_affectation_ids_temp_launch'
    )

    # User-interface
    position_fully_affected = fields.Boolean(
        compute='_compute_affectation_status'
    )
    
    #===== CRUD hooks =====#
    def write(self, vals):
        self._inverse_affectation_ids_temp(vals)
        return super().write(vals)
    
    #===== Compute =====
    @api.depends('position_ids.state')
    def _compute_affectation_status(self):
        """ Position's affectation status at project-scope """
        for project in self:
            project.position_fully_affected = (
                not project.position_ids.ids
                or set(project.position_ids.mapped('state')) == {'done'}
            )
    def _get_warning_banner(self):
        return not self.position_fully_affected
    

    @api.depends('position_ids.quantity')
    def _compute_position_count(self):
        rg_result = self.env['carpentry.position'].read_group(
            domain=[('project_id', 'in', self.ids)],
            fields=['position_id_count:count(id)'],
            groupby=['project_id']
        )
        mapped_qties = {x['project_id'][0]: x['position_id_count'] for x in rg_result}
        for project in self:
            project.position_count = mapped_qties.get(project.id, 0)

    # Temp<->real affectation logics
    def _compute_affectation_ids_temp_phase(self):
        for project in self:
            matrix = project.phase_ids._get_affectation_ids_temp()
            project.affectation_ids_temp_phase = matrix
    def _compute_affectation_ids_temp_launch(self):
        for project in self:
            project.affectation_ids_temp_launch = project.launch_ids._get_affectation_ids_temp()
    def _inverse_affectation_ids_temp(self, vals):
        """ Affectations: call _inverse matrix method of related carpentry's model
            Warning: since affectation_ids_temp_... are computed, `write()` has not effect on those fields, so we look for
            user updated-values in `vals` dict, which are in Command.set format [1/2/3/4/5/6, _, _]
        """
        prefix = 'affectation_ids_temp_'
        for group in [group for group in ['phase', 'launch'] if prefix + group in vals.keys()]:
            vals_command = vals[prefix + group] # [2, id, vals] if updated
            vals_updated = {vals[1]: vals[2] for vals in vals_command if vals[0] == 1 and vals[2]} # [{temp_id: new_vals}]
            self[group + '_ids']._inverse_affectation_ids_temp(vals_updated)
