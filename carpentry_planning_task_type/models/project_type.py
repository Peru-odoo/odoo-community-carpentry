# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

from random import randint

class ProjectType(models.Model):
    _inherit = ['project.type']
    _rec_name = 'display_name'
    
    #===== Fields methods =====#
    def _get_default_color(self):
        return randint(1, 11)

    #===== Fields =====#
    root_type_id = fields.Many2one(
        comodel_name='project.type',
        string='Root Type',
        compute='_compute_root_type_id',
        store=True,
        readonly=True
    )
    sequence = fields.Integer()
    color = fields.Integer(
        string='Color',
        default=_get_default_color
    )
    # --- for planning ---
    code = fields.Char(
        string='Shortname',
        help='Name on planning cards'
    )
    shortname = fields.Char(
        related='code',
        string='Shortname (planning)'
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

    #===== Compute : display_name =====#
    @api.depends('name')
    def _compute_display_name(self):
        for type in self:
            type.display_name = type._get_display_name_one()
    
    def _get_display_name_one(self):
        return self.name
