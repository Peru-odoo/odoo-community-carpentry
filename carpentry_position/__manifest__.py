# -*- coding: utf-8 -*-
{
    'name': "Position",
    'summary': "Create and affect positions in lots, phases and launches (core module)",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': False,
    'installable': True,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.2.0',

    'depends': [
        'project',
        'web_widget_numeric_step', # OCA
        'project_favorite_switch', # other
        'carpentry_base', 'carpentry_project', # carpentry
    ],
    'demo': [
        'demo/carpentry.group.lot.csv',
        'demo/carpentry.position.csv',
        'demo/carpentry.group.phase.csv',
        'demo/carpentry_group_launch.xml',
    ],
    'data': [
        # security
        'security/ir.model.access.csv',
        # views
        'views/carpentry_affectation.xml',
        'views/carpentry_position.xml',
        'views/carpentry_group_lot.xml',
        'views/carpentry_group_phase.xml',
        'views/carpentry_group_launch.xml',
        'views/carpentry_group_menus.xml',
        'views/project_project.xml',
    ],
}


