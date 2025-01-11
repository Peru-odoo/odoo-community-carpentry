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
        # required on the view. Must not be in ORM because of replenishment (stock.warehouse.orderpoint)
        required=False
    )
    description = fields.Char(
        string='Description'
    )
    
    def _compute_display_name(self):
        for mo in self:
            mo.display_name = '[{}] {}' . format(mo.name, mo.description) if mo.description else mo.name

    def _prepare_picking(self):
        """ Write project from PO to procurement group and picking """
        vals = super()._prepare_picking()

        self.group_id.project_id = self.project_id # procurement group
        return vals | {'project_id': self.project_id.id} # picking
