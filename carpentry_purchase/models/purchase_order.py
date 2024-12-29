# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
import base64
from collections import defaultdict

class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['purchase.order', 'project.default.mixin']
    _rec_name = 'display_name'

    #====== Fields ======#
    project_id = fields.Many2one(
        # can be significated as mandatory to users
        # by settings project's analytic plan as mandatory
        required=False
    )
    description = fields.Char(
        string='Description'
    )
    attachment_ids = fields.One2many(
        comodel_name='ir.attachment',
        inverse_name='res_id',
        string='Attachments',
        domain=[('res_model', '=', _name)],
    )
    
    def _compute_display_name(self):
        for mo in self:
            mo.display_name = '[{}] {}' . format(self.name, self.description) 
