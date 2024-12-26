# -*- coding: utf-8 -*-
{
    'name': "Carpentry Purchase",
    'summary': "Delivery to construction site",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': True,
    'installable': True,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'project', # odoo
        'project_purchase_link', # OCA
        'carpentry_base', # carpentry
        ],
    'data': [
        # data
        'views/project_project.xml',
        'views/project_purchase_link.xml',
        'views/purchase_order.xml',
    ]
}


