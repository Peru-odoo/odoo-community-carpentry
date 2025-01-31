# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class Project(models.Model):
    _inherit = ["project.project"]

    #====== Fields ======#
    delivery_address_id = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery address',
        context="""{
            'default_parent_id': partner_id,
            'default_type': 'delivery',
            'show_address_only': 1,
            'address_inline': 1,
        }""",
        domain="""['|',
            ('id', '=', partner_id),
            '&', ('type', '=', 'delivery'), ('id', 'child_of', partner_id)
        ]""",
        help="Delivery address of the construction site, within the customer's"
             " addresses of type 'Delivery'."
    )
    
    #====== Compute ======#
    @api.onchange('partner_id')
    def _prefill_delivery_address(self):
        """ Suggest delivery addresses depending partner_id """
        for project in self:
            addresses = project.partner_id.address_get(['contact', 'delivery'])
            project.delivery_address_id = addresses['delivery']
