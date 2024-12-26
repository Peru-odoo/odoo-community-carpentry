# -*- coding: utf-8 -*-
{
    'name': "Carpentry MRP",
    'summary': "Import components and product Positions through Work Orders",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': True,
    'installable': True,
    'auto_install': False,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'project_favorite_switch', # other
        'carpentry_base', # carpentry
    ],
    'data': [
        # data
        'views/project_project.xml',
        'views/project_purchase_link.xml',
        'views/purchase_order.xml',
    ]
}


