# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions, _, Command
from collections import defaultdict

class ProjectAssignment(models.Model):
    _inherit = ["project.assignment"]

    @api.model
    def _read_group_role_id(self, records, domain, order):
        """ View all role in assignation kanban view """
        return records.search([], order=order)
    
    role_id = fields.Many2one(
        group_expand='_read_group_role_id'
    )
