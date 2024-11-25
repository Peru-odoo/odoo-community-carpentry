# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

class ProductTemplate(models.Model):
    _inherit = ["product.template"]

    detailed_type = fields.Selection(
        # needed for in-code groupby per those categories
        # like budget sum per Carpentry Group (positions, launches, phases, ...)
        selection_add=[
            ('service_prod', 'Service (production))'),
            ('service_install', 'Service (on-site installation)'),
            ('service_office', 'Service (office)'),
            ('consu_project_global', 'Consumable (project global fees)'),
        ],
        ondelete={
            'service_prod': 'set service',
            'service_install': 'set service',
            'service_office': 'set service',
            'consu_project_global': 'set consu'
        })

    def _detailed_type_mapping(self):
        return super()._detailed_type_mapping() | {
            'service_prod': 'service',
            'service_install': 'service',
            'service_office': 'service',
            'consu_project_global': 'consu',
        }
    