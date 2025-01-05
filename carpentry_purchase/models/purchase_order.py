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
        # Attachments not within a message
        comodel_name='ir.attachment',
        inverse_name='res_id',
        string='Attachments',
        domain=[('res_model', '=', _name), ('message_ids', '=', [])],
    )
    
    def _compute_display_name(self):
        for mo in self:
            mo.display_name = '[{}] {}' . format(self.name, self.description) 

    def action_rfq_send(self):
        action = super().action_rfq_send()
        action['context'] |= {
            'default_attachment_ids': action['context'].get('default_attachment_ids', []) + [Command.set(self.attachment_ids.ids)]
        }