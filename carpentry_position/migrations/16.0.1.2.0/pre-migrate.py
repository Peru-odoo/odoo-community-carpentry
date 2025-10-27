# -*- coding: utf-8 -*-

import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    _alter_tables(cr)

def _alter_tables(cr):
    # access to ir.model
    cr.execute("DELETE FROM ir_model_access WHERE name = 'CarpentryIrModel'")
    
    # field readonly_affectation now computed
    cr.execute("""
        ALTER TABLE carpentry_group_lot     DROP COLUMN IF EXISTS readonly_affectation;
        ALTER TABLE carpentry_group_phase   DROP COLUMN IF EXISTS readonly_affectation;
        ALTER TABLE carpentry_group_launch  DROP COLUMN IF EXISTS readonly_affectation;
        ALTER TABLE carpentry_position      DROP COLUMN IF EXISTS readonly_affectation;
        ALTER TABLE project_project         DROP COLUMN IF EXISTS readonly_affectation;
    """)



