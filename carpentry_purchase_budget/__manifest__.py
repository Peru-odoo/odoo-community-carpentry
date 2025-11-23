# -*- coding: utf-8 -*-
{
    'name': "Purchase Budget",
    'summary': "Consume positions budget from purchases expense",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': False,
    'installable': True,
    'auto_install': False,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.2.1',

    'depends': ['carpentry_purchase', 'carpentry_position_budget'],
    'data': [
        # report
        'report/carpentry_budget_remaining.xml',
        # security
        'security/ir.model.access.csv',
    ],
    'post_init_hook': 'post_init_hook', # rebuild budget expense sql view
    'uninstall_hook': 'uninstall_hook',
}
