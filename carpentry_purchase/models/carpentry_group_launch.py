# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class CarpentryGroupLaunch(models.Model):
    _inherit = ['carpentry.group.launch']
    
    purchase_ids = fields.Many2many(
        comodel_name='purchase.order',
        relation='purchase_order_launch_rel',
        string='Purchase Orders',
    )
    task_ids = fields.One2many(
        comodel_name='project.task',
        inverse_name='launch_id',
        string='Needs'
    )
