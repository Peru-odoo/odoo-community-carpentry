# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID, exceptions

import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    # convert `section_id` and `record_model_id` into balance_id, purchase_id, task_id, ...
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
    to_unlink = []
    for row in cr.fetchall():
        (id, record_id, record_model_id) = row
        reservation = Reservation.browse(id).with_context(silence_constrain_amount_reserved=True)
        record_res_model = Reservation[mapped_fields[record_model_id]]._name
        record = env[record_res_model].with_context(active_test=False).browse(record_id)
        if record.exists():
            reservation.write({mapped_fields[record_model_id]: record_id})
        else:
            to_unlink.append(id)
    
    # clean orphan reservations (e.g. not existing purchase_id)
    print('to_unlink', to_unlink)
    cr.execute("DELETE FROM carpentry_budget_reservation WHERE id IN %s", (tuple(to_unlink), ))

    # update stored totals
    reservations = Reservation.search([('id', 'not in', to_unlink)])
    for record_field in Reservation._get_record_fields():
        records = reservations[record_field].with_context(silence_constrain_amount_reserved=True)

        rg_result = records._get_rg_result_expense()
        records._compute_total_expense_gain(rg_result=rg_result)
        records._compute_total_budget_reserved(rg_result=rg_result)
    
    cr.execute("""
        DROP TABLE IF EXISTS carpentry_budget_reservation_migration CASCADE;
    """)
