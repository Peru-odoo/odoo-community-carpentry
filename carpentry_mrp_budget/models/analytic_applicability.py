# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountAnalyticApplicability(models.Model):
    _inherit = ['account.analytic.applicability']

    business_domain = fields.Selection(
        selection_add=[
            ('manufacturing_order', 'Manufacturing Order'),
            ('picking', 'Picking'),
        ],
        ondelete={
            'manufacturing_order': 'set general',
            'picking': 'set general',
        }
    )
