# -*- coding: utf-8 -*-
{
    'name': "Carpentry Equipment",
    'summary': "Manage equipment fleet, on-field usage and their maintenance.",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': True,
    'installable': True,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.0',

    'depends': [
        'maintenance', # Odoo CE
        'base_maintenance_group', 'maintenance_equipment_image', 'maintenance_equipment_usage', # OCA
        'carpentry_project', # carpentry
    ],
    'data': [
        # data
        # views
        # 'views/project_project.xml',
    ],
}
