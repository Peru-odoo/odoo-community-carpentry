# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

class CarpentryGroupLot(models.Model):
    _inherit = ['carpentry.group.lot']

    # import
    external_db_guid = fields.Char(string='Last External DB ID')
