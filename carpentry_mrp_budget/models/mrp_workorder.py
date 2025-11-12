# -*- coding: utf-8 -*-

from odoo import models

class WorkOrder(models.Model):
    _inherit = ['mrp.workorder']
    _record_field = 'production_id'
