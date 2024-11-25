# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryGroupLot(models.Model):
    _inherit = 'carpentry.group.lot'

    external_db_id = fields.Integer(
        string='External database ID'
    )
