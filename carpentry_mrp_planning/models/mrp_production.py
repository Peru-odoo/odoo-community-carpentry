# -*- coding: utf-8 -*-

from odoo import models, fields

class ManufacturingOrder(models.Model):
    _inherit = ['mrp.production']
    
    active = fields.Boolean(
        default=True
    )
