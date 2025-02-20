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
        'project_role_visibility', # for access rules
        'mrp_project_link', 'mrp_attendance', 'mrp_productivity_qty', # other
        'carpentry_purchase', # carpentry
    ],
    'data': [
        # security
        'security/ir.model.access.csv',
        'security/project_security.xml',
        # data
        'views/mrp_production.xml',
        'views/product_template.xml',
        'views/stock_picking.xml',
        'views/stock_quant.xml',
    ]
}
