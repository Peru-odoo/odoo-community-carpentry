# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
import base64
from collections import defaultdict

class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['purchase.order', 'project.default.mixin']

    #====== Fields ======#
    project_id = fields.Many2one(
        # can be significated as mandatory to users by settings project's analytic plan as mandatory
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
    
    #====== Compute ======#
    # adresses
    @api.onchange('partner_id')
    def _prefill_delivery_address(self):
        """ Suggest delivery addresses depending partner_id """
        for project in self:
            addresses = project.partner_id.address_get(['contact', 'invoice'])
            project.delivery_address_id = addresses['delivery']
