# -*- coding: utf-8 -*-
{
    'name': "Carpentry Warranty Aftersale",
    'summary': "Distinguish construction warranty expenses from standard project lifetime expenses and manage after-sale as sub-projects.",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': True,
    'installable': True,
    'category': 'Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'project_parent_sequence', # carpentry
    ],
    'data': [
        # data
        # views
        'views/project_project.xml',
    ],
}


