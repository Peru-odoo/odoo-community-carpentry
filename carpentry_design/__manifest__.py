# -*- coding: utf-8 -*-
{
    'name': "Carpentry Design",
    'summary': "Manage plan publishing and visa feedback (optional core module)",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': True,
    'installable': True,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'project', # odoo
        'project_role_visibility', # other (for security access)
        'project_favorite_switch', # other
        'carpentry_base', 'carpentry_planning', 'carpentry_position', # carpentry
    ],

    'data': [
        # data
        'data/carpentry.planning.column.xml',
        # security
        'security/carpentry_design_security.xml',
        'security/ir.model.access.csv',
        # views
        'views/carpentry_plan_release.xml',
        'views/carpentry_plan_set.xml',
        'views/carpentry_planning.xml',
        'views/project_project.xml',
    ],
    'post_init_hook': 'post_init_hook', # rebuild sql view
    'uninstall_hook': 'uninstall_hook',
}
