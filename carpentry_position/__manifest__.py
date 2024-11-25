# -*- coding: utf-8 -*-
{
    'name': "Carpentry Position",
    'summary': "Create and affect positions in lots, phases and launches (core module)",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': False,
    'installable': True,
    'category': 'Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'web_widget_numeric_step', 'web_widget_x2many_2d_matrix', # OCA
        'project_sequence', 'project_favorite_switch', # other
        'carpentry_base', # carpentry
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
}


