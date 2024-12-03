# -*- coding: utf-8 -*-
{
    'name': "Carpentry Position Budget",
    'summary': "Import budget on positions and manage goods and worktime budgets per project (core module)",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': False,
    'installable': True,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        # odoo
        'hr_timesheet', # only for company.internal_project_id
        'sales_team', # for security access
        'web_notify', # OCA
        'project_role_visibility', # other (for security access)
        'project_favorite_switch', 'project_budget', 'utilities_file_management', # other
        'carpentry_base', 'carpentry_project', 'carpentry_position', 'carpentry_planning', # carpentry
    ],
    'data': [
        # security
        'security/carpentry_position_budget_security.xml',
        'security/ir.model.access.csv',
        # wizard
        'wizard/carpentry_position_merge_wizard.xml',
        'wizard/carpentry_position_budget_import_wizard.xml',
        # views
        'views/carpentry_groups.xml',
        'views/carpentry_position_budget_interface.xml',
        'views/carpentry_position_budget.xml',
        'views/carpentry_position.xml',
        'views/project_project.xml',
        'views/account_move_budget_line.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'carpentry_position_budget/static/src/**/*',
        ],
    },
}
