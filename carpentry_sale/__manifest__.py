# -*- coding: utf-8 -*-
{
    'name': 'Carpentry Sale',
    'summary': "Manage project's market and reviews (quotations), shared fees and margins compared to budget.",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': True,
    'installable': True,
    'category': 'Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'sale_project', 'sale_management', # Odoo
        'sale_project_link', 'crm_project_link', # other
        'carpentry_base', # carpentry
    ],
    'data': [
        'views/project_project.xml',
        'views/project_task.xml',
        'views/sale_order.xml',
    ],
}
