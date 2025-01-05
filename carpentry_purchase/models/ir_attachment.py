# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
import base64
from collections import defaultdict

class IrAttachment(models.Model):
    _inherit = ['ir.attachment']

    # Reverse M2M, to filter attachment not related to a message
    message_ids = fields.Many2many(
        comodel_name='ir.attachment',
        inverse_name='message_attachment_rel',
        column1='attachment_id',
        column2='message_id',
        string='Attachments'
    )
