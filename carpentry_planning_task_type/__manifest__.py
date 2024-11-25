# -*- coding: utf-8 -*-
{
    'name': "Carpentry Milestones, Meetings and Instructions",
    'summary': "Manage specific tasks' types with customized feature per type, and follow their progress in Planning.",
    'author': 'Arnaud LAYEC',
    'website': 'https://github.com/arnaudlayec/odoo-community-carpentry',
    'license': 'AGPL-3',

    'application': False,
    'installable': True,
    'category': 'Carpentry',
    'version': '16.0.1.0.1',

    'depends': [
        'add_attachment_to_report', # other (external)
        'project_type',  # OCA
        'project_favorite_switch', 'project_task_default_assignee', 'project_task_copy', 'project_task_attachment', # other
        'carpentry_base', 'carpentry_planning_task', # carpentry
    ],
    'data': [
        # data
        'data/project.type.csv',
        # report
        'report/task_report.xml',
        # views
        'views/project_type.xml',
        'views/project_task_base.xml',
        'views/project_task_meeting.xml',
        'views/project_task_milestone.xml',
        'views/project_task_instruction.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'carpentry_planning_task_type/static/src/**/*',
        ]
    },
}
