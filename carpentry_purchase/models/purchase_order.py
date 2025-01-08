# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
import base64
from collections import defaultdict

class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['purchase.order', 'project.default.mixin']
    _rec_name = 'display_name'

    #====== Fields ======#
    description = fields.Char(
        string='Description'
    )
    
    def _compute_display_name(self):
        for mo in self:
            mo.display_name = '[{}] {}' . format(mo.name, mo.description) if mo.description else mo.name

    def _prepare_picking(self):
        """ Write project from PO to picking """
        return super()._prepare_picking() | {
            'project_id': self.project_id.id
        }
