# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command

class CarpentryPlanningColumn(models.Model):
    _inherit = "carpentry.planning.column"

    column_id_need_date = fields.Many2one(
        comodel_name='carpentry.planning.column',
        string='Needs milestone column',
        help='Column whose `start` milestone will be used as reference to compute'
            ' needs automated deadline. If none, same column\'s milestones as the'
            ' needs cards will be used.'
    )
    