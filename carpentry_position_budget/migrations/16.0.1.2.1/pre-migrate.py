# -*- coding: utf-8 -*-

import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    cr.execute("""
        ALTER TABLE carpentry_budget_reservation
            RENAME COLUMN sequence_section TO sequence_record;
        CREATE TABLE carpentry_budget_reservation_migration AS carpentry_budget_reservation;
    """)
