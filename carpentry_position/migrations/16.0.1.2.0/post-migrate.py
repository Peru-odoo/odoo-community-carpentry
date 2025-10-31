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
    Affectation = env['carpentry.affectation'].with_context(active_test=False)

    # phase & launchs affectations
    cr.execute("""
        SELECT
            REPLACE(group_model.model, 'carpentry.group.', ''),
            affectation.group_id, -- `phase_id` or `launch_id`
            parent_affectation.group_id, -- parent_group_id (phase_id)
            CASE -- position_id
                WHEN group_model.model = 'carpentry.group.phase'
                THEN affectation.record_id
                ELSE parent_affectation.record_id
            END,
            affectation.quantity_affected,
            affectation.affected,
            parent_affectation.quantity_affected
        FROM
            carpentry_group_affectation AS affectation
        INNER JOIN 
            ir_model AS group_model
            ON group_model.id = affectation.group_model_id
        LEFT JOIN
            carpentry_group_affectation AS parent_affectation
            ON  parent_affectation.id = affectation.record_id
        WHERE group_model.model IN ('carpentry.group.phase', 'carpentry.group.launch')
    """)
    vals_list = []
    for row in cr.fetchall():
        (
            mode, group_id, parent_group_id, position_id,
            quantity_affected, affected, parent_quantity_affected
        ) = row
        position = env['carpentry.position'].browse(position_id)
        phase    = env['carpentry.group.phase'].browse(group_id if mode == 'phase' else parent_group_id)
        launch   = env['carpentry.group.launch'].browse(group_id if mode == 'launch' else 0)

        if not position.exists() or not phase.exists() or not launch.exists():
            continue

        vals = {
            'mode': mode,
            'project_id': position.project_id.id,
            'position_id': position.id,
            'lot_id': position.lot_id.id,
            'phase_id': phase.id,
            'launch_id': launch.id,
            'sequence_position': position.sequence,
            'sequence_group': phase.sequence if mode == 'phase' else launch.sequence,
            'sequence_parent_group': position.lot_id.sequence if mode == 'phase' else phase.sequence,
            'affected': affected if mode == 'launch' else False,
            'quantity_affected': quantity_affected if mode == 'phase' else parent_quantity_affected,
            'active': all([
                position.active,
                position.project_id.active,
                position.lot_id.active,
                phase.active,
                launch.active if mode == 'launch' else True,
            ]),
        }
        vals_list.append(vals)
    Affectation.create(vals_list)

    # keep carpentry_group_affectation for `carpentry_position_budget`
    cr.execute("""
        ALTER TABLE carpentry_group_affectation
               RENAME TO carpentry_group_affectation_migration;
    """)
