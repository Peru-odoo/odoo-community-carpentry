# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    # convert `record_model_id` into balance_id, purchase_id, task_id, ...
    IrModel = env['ir.model']
    Reservation = env['carpentry.budget.reservation']
    mapped_fields = {
        IrModel._get_id(Reservation[record_field]._name): record_field
        for record_field in Reservation._get_record_fields()
    }
    cr.execute("""
        SELECT id, section_id, section_model_id
        FROM carpentry_budget_reservation_migration
    """)
    for row in cr.fetchall():
        (id, record_id, record_model_id) = row
        Reservation.browse(id).write({
            mapped_fields[record_model_id]: record_id
        })
    
    cr.execute("""
        DROP TABLE IF EXISTS carpentry_budget_reservation_migration CASCADE;
    """)
