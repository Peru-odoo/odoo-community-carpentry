# -*- coding: utf-8 -*-
{
    'name': "Warranty Aftersale",
    'summary': "Identify warranty expenses and manage after-sale sub-projects (optional).",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': True,
    'installable': True,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'carpentry_base',
        'project_children_sequence', # carpentry
    ],
    'demo': [
        'demo/account.analytic.plan.csv',
        'demo/account.analytic.account.csv',
    ],
    'data': [
        # data
        # views
        # 'views/project_project.xml',
    ],
}


