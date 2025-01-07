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
    attachment_ids = fields.One2many(
        # Attachments not within a message
        comodel_name='ir.attachment',
        inverse_name='res_id',
        string='Attachments',
        domain=[('res_model', '=', _name), ('message_ids', '=', False)],
    )
    
    def _compute_display_name(self):
        for mo in self:
            mo.display_name = '[{}] {}' . format(mo.name, mo.description) 

    def action_rfq_send(self):
        action = super().action_rfq_send()
        action['context'] |= {
            'default_attachment_ids': action['context'].get('default_attachment_ids', []) + [Command.set(self.attachment_ids.ids)]
        }
        return action

    def _prepare_picking(self):
        """ Write project from PO to picking """
        return super()._prepare_picking() | {
            'project_id': self.project_id.id
        }
