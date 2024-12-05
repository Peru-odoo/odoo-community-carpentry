# -*- coding: utf-8 -*-
{
    'name': "Carpentry Timesheet",
    'summary': "Track timesheet per project budgets",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',
    
    'application': False,
    'installable': True,
    'category': 'Carpentry/Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'hr_timesheet_sheet', # OCA
        'project_favorite_switch', # other
        'project_budget_timesheet', 'hr_timesheet_sheet_copy', 'project_task_analytic_hr', 'project_task_analytic_type', # other
        'carpentry_base', 'carpentry_planning', # carpentry
        'carpentry_position_budget', # for 'Budget' menu
    ],
    'data': [
        # views
        'views/carpentry_planning.xml',
        'views/hr_views.xml',
        'views/project_task.xml',
        'views/account_analytic_account.xml',
        # report
        'report/hr_timesheet_report_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'carpentry_timesheet/static/src/**/*',
        ]
    }
}
