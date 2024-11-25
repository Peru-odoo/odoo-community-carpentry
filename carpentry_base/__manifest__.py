# -*- coding: utf-8 -*-
{
    'name': "Carpentry (base)",
    'summary': """Carpentry base module (settings, ...), not relevant by itself""",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': False,
    'installable': True,
    'category': 'Carpentry',
    'version': '16.0.1.0.1',

    'depends': ['project'],
    'data': [
        # views
        # 'views/res_config_settings.xml',
        'views/project_project.xml',
    ]
}
