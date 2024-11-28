# -*- coding: utf-8 -*-
{
    'name': "Carpentry Planning Tasks",
    'summary': "Link projects Tasks to plannings cards and the others as Global Tasks (optional).",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': False,
    'installable': True,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'project_timeline', 'project_task_link', # OCA
        'project_favorite_switch', # other
        'carpentry_base', 'carpentry_planning',
    ],
    'data': [
        # views
        'views/carpentry_planning.xml',
        'views/project_task_planning.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'carpentry_planning_task/static/src/**/*',
        ]
    }
}


