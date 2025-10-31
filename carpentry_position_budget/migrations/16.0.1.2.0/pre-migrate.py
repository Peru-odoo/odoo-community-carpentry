# -*- coding: utf-8 -*-

import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    # if not version:
    #     return
    # env = api.Environment(cr, SUPERUSER_ID, {})

    # views
    cr.execute("""
        DELETE FROM ir_ui_view WHERE arch_prev LIKE '%%amount_budgetable%%';
        DELETE FROM ir_ui_view WHERE arch_prev LIKE '%total_budget_reserved%' AND type = 'tree';
    """)

    # tables: positions, affectations, ...
    cr.execute("""
        ALTER TABLE carpentry_position_budget
               RENAME COLUMN amount TO amount_unitary;
    """)
    
    # sections tables
    models = ('project_task', 'purchase_order', 'stock_picking', 'mrp_production', 'carpentry_budget_balance')
    for model in models:
        cr.execute(f"""
            ALTER TABLE {model}
                DROP COLUMN IF EXISTS readonly_affectation CASCADE,
                DROP COLUMN IF EXISTS total_budget_reserved CASCADE,
                DROP COLUMN IF EXISTS currency_id CASCADE;
        """)

    # many2many tables
    cr.execute("""
        ALTER TABLE carpentry_group_affectation_budget_mrp_analytic_rel
               RENAME TO carpentry_budget_mrp_analytic_rel;
        ALTER TABLE carpentry_group_affectation_budget_picking_analytic_rel
               RENAME TO carpentry_budget_picking_analytic_rel;
    """)

    # budget_type
    models = (
        'account_analytic_account', 'account_move_budget_line',
        'carpentry_position_budget', 'carpentry_group_affectation_migration',
    )
    for model in models:
        cr.execute(f"UPDATE {model} SET budget_type = 'other' WHERE budget_type = 'project_global_cost'")
    cr.execute("""
        UPDATE carpentry_planning_column
        SET budget_types = REPLACE(budget_types, 'project_global_cost', 'other')
        WHERE budget_types LIKE '%project_global_cost%'
    """)
