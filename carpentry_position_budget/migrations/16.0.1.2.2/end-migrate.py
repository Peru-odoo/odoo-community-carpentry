# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    # compute `budget_project_ids`
    env['account.move.line'].search([])._inverse_analytic_distribution()
