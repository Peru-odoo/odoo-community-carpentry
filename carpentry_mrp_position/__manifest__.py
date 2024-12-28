# -*- coding: utf-8 -*-
{
    'name': "Carpentry MRP Position",
    'summary': "Manufacture positions as final products",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': False,
    'installable': True,
    'auto_install': False,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': ['carpentry_mrp_import'],
    'data': [
        # data
        'views/mrp_production.xml',
        'views/product_template.xml',
    ]
}


