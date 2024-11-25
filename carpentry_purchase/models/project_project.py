# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.osv import expression

from collections import defaultdict
import datetime

class Project(models.Model):
    _inherit = "project.project"

    #====== Fields ======#
    # adresses
    partner_delivery_id = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery address',
        context={'show_address_only': 1},
        help="Default delivery address for orders to be delivered on the construction site."
             " Can be the main address of client or any 'delivery' address(es) of the client."
    )
    partner_invoice_id = fields.Many2one(
        comodel_name='res.partner',
        string='Invoicing address',
        context={'show_address_only': 1},
        help="Default invoicing address for project's invoicing."
             " Can be the main address of client or any 'invoicing' address(es) of the client."
    )
    
    #====== Compute ======#
    # adresses
    @api.onchange('partner_id')
    def _prefill_project_addresses(self):
        """ Suggest delivery & invoicing addresses depending partner_id """
        for project in self:
            addresses = project.partner_id.address_get(['contact', 'delivery', 'invoice'])
            
            project.partner_delivery_id = addresses['delivery']
            project.partner_invoice_id = addresses['invoice']
