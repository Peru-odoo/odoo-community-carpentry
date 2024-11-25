# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class ProjectType(models.Model):
    _inherit = ['project.type']

    #===== Fields =====#
    code = fields.Char(
        # for planning card
        string='Shortname',
        help='Name on planning cards'
    )
    shortname = fields.Char(
        # for planning card
        related='code',
        string='Shortname (planning)'
    )
    sequence = fields.Integer()
    root_type_id = fields.Many2one(
        comodel_name='project.type',
        string='Root Type',
        compute='_compute_root_type_id',
        store=True,
        readonly=True
    )

    #===== Constrains & compute: root type =====#
    def check_parent_id(self):
        """ Override to allow recursivity """
        return
    
    @api.ondelete(at_uninstall=False)
    def _unlink_except_not_root(self):
        """ Prevent unlink if root """
        for type in self:
            if not type.root_type_id.id: # is root
                raise exceptions.ValidationError(
                    _('Root types cannot be removed.')
                )
    
    @api.depends('parent_id')
    def _compute_root_type_id(self):
        """ Recursively find and store root type """
        for type in self:
            root_type_id = type.parent_id
            while root_type_id.parent_id.id:
                root_type_id = root_type_id.parent_id
            type.root_type_id = root_type_id
