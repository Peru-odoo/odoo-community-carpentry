# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command
from datetime import date

class CarpentryGroupMixin(models.AbstractModel):
    """ Basic fields and features commun to some carpentry models, related to projects
        Like for: Phases, Launches, Purchase Order, Fab Order, Plan set, ...
    """
    _name = "carpentry.group.mixin"
    _description = 'Group of Positions'
    _order = "sequence"
    _inherit = ["project.default.mixin"]

    #===== Fields =====#
    # base
    name = fields.Char(
        string='Name',
        required=True,
        index='trigram'
    )
    company_id = fields.Many2one(
        related='project_id.company_id'
    )
    active = fields.Boolean(
        string="Active?",
        default=True
    )
    
    # computed / useful
    sequence = fields.Integer(
        string="Sequence",
        compute='_compute_sequence',
        store=True,
        copy=False
    )

    _sql_constraints = [(
        "name_per_project",
        "UNIQUE (name, project_id)",
        "This name already exists within the project."
    )]
    
    #===== Compute =====#
    @api.depends('project_id')
    def _compute_sequence(self):
        self = self.with_context(active_test=False)
        
        rg_result = self.read_group(
            domain=[('project_id', 'in', self.project_id.ids)],
            groupby=['project_id'],
            fields=['sequence:max']
        )
        mapped_data = {x['project_id'][0]: x['sequence'] for x in rg_result}
        for group in self:
            group.sequence = mapped_data.get(group.project_id.id, 0) + 1
            mapped_data[group.project_id.id] = group.sequence
