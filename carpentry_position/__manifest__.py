# -*- coding: utf-8 -*-
{
    'name': "Carpentry Position",
    'summary': "Create and affect positions in lots, phases and launches (core module)",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': False,
    'installable': True,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'project',
        'web_widget_numeric_step', 'web_widget_x2many_2d_matrix', # OCA
        'project_favorite_switch', # other
        'carpentry_base', 'carpentry_project', # carpentry
    ],
    'data': [
        # views
        'views/carpentry_affectation.xml',
        'views/carpentry_groups.xml',
        'views/carpentry_position.xml',
        'views/project_project.xml',
        # security
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'carpentry_position/static/src/**/*',
        ],
    },
}


