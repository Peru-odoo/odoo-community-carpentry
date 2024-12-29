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
    'version': '16.0.1.0.1',

    'depends': ['carpentry_purchase', 'carpentry_position_budget'],
    'data': [
        'views/purchase_order.xml',
    ]
}
