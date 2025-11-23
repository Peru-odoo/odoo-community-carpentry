# -*- coding: utf-8 -*-

import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    # update fields name
    cr.execute("""
        ALTER TABLE carpentry_budget_reservation
            RENAME COLUMN sequence_section TO sequence_record;
    """)

    # keep original table for `end-migrate.py`
    cr.execute("""
        CREATE TABLE IF NOT EXISTS carpentry_budget_reservation_migration AS (
            SELECT id, section_id, section_model_id
            FROM carpentry_budget_reservation
        );
    """)
