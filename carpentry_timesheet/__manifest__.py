# -*- coding: utf-8 -*-
{
    'name': "Carpentry Timesheet",
    'summary': "Timesheet on Carpentry budget",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',
    
    'application': False,
    'installable': True,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'hr_timesheet', # odoo
        'project_task_link', # OCA
        'project_favorite_switch', # other
        'carpentry_base', 'carpentry_position_budget', # carpentry
    ],
    'assets': {
        'web.assets_backend': [
            'carpentry_timesheet/static/src/**/*',
            'carpentry_timesheet/static/src/**/*',
        ],
    },
    'data': [
        'views/project_task_views.xml',
        'views/project_views.xml',
        'views/carpentry_planning_views.xml',
        'views/hr_views.xml',
        'views/product_views.xml',
        'report/hr_timesheet_report_view.xml',
    ],
}
