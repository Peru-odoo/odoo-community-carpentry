# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    _migrate_carpentry_affectation(cr, env)

def _migrate_carpentry_affectation(cr, env):
    Affectation = env['carpentry.affectation']

    # phase affectations
    cr.execute("""
        SELECT
            group_model.model,
            affectation.record_id,
            affectation.group_id,
            affectation.quantity_affected,
            affectation.affected,
            affectation.position_id,
            parent.group_id -- phase_id
        FROM
            carpentry_group_affectation AS affectation
        INNER JOIN 
            ir_model AS group_model
            ON group_model.id = affectation.group_model_id
        LEFT JOIN
            carpentry_group_affectation AS parent
            ON  parent.id = affectation.record_id
            AND affectation.record_model_id = (SELECT id FROM ir_model WHERE model = 'carpentry.group.affectation')
    """)
    vals_list = []
    for row in cr.fetchall():
        mode = row[0].replace('carpentry.group.', '')
        if mode not in ('phase', 'launch'):
            continue
        
        position = env['carpentry.position'].browse(row[5])
        phase    = env['carpentry.group.phase'].browse(row[2] if mode == 'phase' else row[6])
        group    = phase if mode == 'phase' else env['carpentry.group.launch'].browse(row[2])
        parent_group = phase if mode == 'launch' else position.lot_id

        if not position.exists() or not phase.exists() or not group.exists():
            continue

        vals = {
            'mode': mode,
            'project_id': position.project_id.id,
            'position_id': position.id,
            'lot_id': position.lot_id.id,
            'phase_id': phase.id,
            'sequence_position': position.sequence,
            'sequence_group': group.sequence,
            'sequence_parent_group': parent_group.sequence,
            'active': all([
                position.active,
                position.project_id.active,
                position.lot_id.active,
                phase.active,
                group.active, # can be launch
            ]),
        } | (
            {'quantity_affected': row[3]}
            if mode == 'phase' else
            {'affected': row[4]}
        )
        vals_list.append(vals)
    Affectation.create(vals_list)

    # keep carpentry_group_affectation for `carpentry_position_budget`
    cr.execute("""
        ALTER TABLE carpentry_group_affectation
               RENAME TO carpentry_group_affectation_migration;
    """)
