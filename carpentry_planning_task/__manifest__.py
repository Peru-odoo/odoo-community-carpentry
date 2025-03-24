# -*- coding: utf-8 -*-
{
    'name': "Planning Tasks",
    'summary': "Link projects Tasks to plannings cards and the others as Global Tasks (optional).",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': False,
    'installable': True,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'project_task_link', # OCA
        'project_favorite_switch', 'project_task_copy', # other
        'carpentry_base', 'carpentry_planning',
    ],
    'data': [
        # views
        # 'views/carpentry_planning.xml', # [2025-03-24 - ALY] disabled feature
        # 'views/project_task_planning.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'carpentry_planning_task/static/src/**/*',
        ]
    }
}


