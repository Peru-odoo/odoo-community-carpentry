# -*- coding: utf-8 -*-
{
    'name': "Carpentry MRP Orgadata Import",
    'summary': "Import components to Manufacturing Orders (from Orgadata)",
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
        'purchase_discount', # OCA
        'carpentry_base', # carpentry
    ],
    'data': [
        # wizard
        'wizard/carpentry_mrp_import_wizard.xml',
        # views
        'views/mrp_production.xml',
        'views/product_template.xml',
    ]
}


