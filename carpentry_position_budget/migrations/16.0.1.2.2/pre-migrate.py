# -*- coding: utf-8 -*-

import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    # needed because `report` sql is committed before `models`
    cr.execute("""
        CREATE TABLE IF NOT EXISTS public.carpentry_budget_analytic_line_project_rel (
            line_id integer NOT NULL,
            project_id integer NOT NULL
        );
    """)
