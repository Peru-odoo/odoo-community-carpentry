# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class ManufacturingOrder(models.Model):
    _inherit = ['mrp.production']
    