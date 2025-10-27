# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    _migrate_budget_reservation(cr, version)


def _migrate_budget_reservation(cr, version):
    _logger.info("Migrating budget reservation from carpentry.affectation to carpentry.budget.reservation")
    
    cr.execute("""
        INSERT INTO carpentry_budget_reservation AS reservation
        (
            project_id,
            analytic_account_id,
            budget_type,
            launch_id,
            section_id,
            section_model_id,
            project_budget,
            sequence_launch,
            sequence_aac,
            sequence_section,
            amount_reserved,
            active,
            date
        )
        SELECT 
            a.project_id,
            a.group_id AS analytic_account_id,
            a.budget_type,
            CASE
                WHEN record_model.model = 'carpentry.group.launch'
                THEN record_id
                ELSE NULL
            END AS launch_id,
            a.section_id,
            a.section_model_id,
            CASE
                WHEN record_model.model = 'project.project'
                THEN TRUE
                ELSE FALSE
            END AS project_budget,
            CASE
                WHEN record_model.model = 'carpentry.group.launch'
                THEN launch.sequence
                ELSE NULL
            END AS sequence_launch,
            aac.sequence AS sequence_aac,
            a.seq_section AS sequence_section,
            a.quantity_affected AS amount_reserved,
            a.active,
            a.date
        FROM carpentry_group_affectation_migration AS a
               
            INNER JOIN ir_model AS record_model
               ON record_model.id = a.record_model_id
            
            INNER JOIN account_analytic_account AS aac
               ON aac.id = a.group_id
            
            LEFT JOIN carpentry_group_launch AS launch
                ON launch.id = record_id
        
        WHERE a.budget_type IS NOT NULL
    """)

    cr.execute("""
        DROP TABLE IF EXISTS carpentry_group_affectation_migration CASCADE;
    """)
