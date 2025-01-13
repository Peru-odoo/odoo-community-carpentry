# -*- coding: utf-8 -*-
{
    'name': "MRP Positions",
    'summary': "Manufacture positions as final products",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': False,
    'installable': True,
    'auto_install': False,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'mrp', # Odoo CE
        'mrp_project_link', # other
        'carpentry_purchase', # carpentry
    ],
    'data': [
        # data
        'views/mrp_production.xml',
        'views/product_template.xml',
    ]
}
