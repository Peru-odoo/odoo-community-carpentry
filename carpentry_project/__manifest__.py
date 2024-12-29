# -*- coding: utf-8 -*-
{
    'name': "Project",
    'summary': "Slightly adapts Project styling for Carpentry (light core module)",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': False,
    'installable': True,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'project', # Odoo CE
        'base_usability', # akretion
        'project_favorite_switch', 'project_role_visibility', # other (for security access)
        'carpentry_base', # carpentry
    ],
    'data': [
        'views/project_project.xml',
        'views/project_assignment.xml',
        'views/project_role.xml',
    ],
    "uninstall_hook": "uninstall_hook",
}
