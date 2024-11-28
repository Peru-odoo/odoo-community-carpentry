# -*- coding: utf-8 -*-
{
    'name': "Carpentry Design",
    'summary': "Design application for Carpentry, with planset & plans releasing management (optional core module)",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': True,
    'installable': True,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'project', # odoo
        'web_widget_numeric_step', 'project_role', 'project_administrator_restricted_visibility', # OCA
        'project_favorite_switch', # other
        'carpentry_base', 'carpentry_planning', 'carpentry_position', 'carpentry_timesheet' # carpentry
    ],

    'data': [
        # data
        'data/carpentry.planning.column.csv',
        # security
        'security/carpentry_design_security.xml',
        'security/ir.model.access.csv',
        # views
        'views/carpentry_plan_release.xml',
        'views/carpentry_plan_set.xml',
        'views/carpentry_planning.xml',
        'views/project_project.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'carpentry_design/static/src/xml/tree_button.xml',
            'carpentry_design/static/src/js/tree_button.js',
        ],
    },
    'post_init_hook': 'post_init_hook', # rebuild sql view
    'uninstall_hook': 'uninstall_hook',
}
