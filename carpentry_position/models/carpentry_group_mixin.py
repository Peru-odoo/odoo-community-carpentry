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
        rg_result = self.read_group(
            domain=[('project_id', 'in', self.project_id.ids)],
            groupby=['project_id'],
            fields=['sequence:max']
        )
        mapped_data = {x['project_id'][0]: x['sequence'] for x in rg_result}
        for group in self:
            group.sequence = mapped_data.get(group.project_id.id, 0) + 1
            mapped_data[group.project_id.id] = group.sequence

    #===== Affectation method =====#
    def _get_domain_affect(self, group='group', group2_ids=None, group2='record'):
        """ Return domain for search on `carpentry.group.affectation[.temp]`
            :arg self: recordset of `[field]_ids`, like `group_ids`, `section_ids`, ...
        """
        domain = [(group + '_res_model', '=', self._name), (group + '_id', 'in', self.ids)]
        if group2_ids:
            domain += [(group2 + '_res_model', '=', group2_ids._name), (group2 + '_id', 'in', group2_ids.ids)]
        return domain
    