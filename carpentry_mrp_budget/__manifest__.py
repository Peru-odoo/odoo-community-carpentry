# -*- coding: utf-8 -*-
{
    'name': "MRP Budget",
    'summary': "Consume positions budget from workcenter times",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': False,
    'installable': True,
    'auto_install': False,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'mrp_account', # Odoo

        'mrp_workcenter_cost_history', # other

        # carpentry
        'carpentry_mrp',
        'carpentry_purchase_budget',
    ],
    "data": [
        # security
        "security/ir.model.access.csv",
        # views
        "views/mrp_workorder.xml",
        "views/mrp_production.xml",
        "views/stock_picking.xml",
        "views/stock_move.xml",
        "views/stock_valuation_layer.xml",
    ],
    'post_init_hook': 'post_init_hook', # rebuild budget expense sql view
    'uninstall_hook': 'uninstall_hook',
}
