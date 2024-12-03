# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api, Command

def uninstall_hook(cr, registry):
    """ Restore initial menu """
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('project.menu_projects').write({
        'groups_id': [Command.set(env.ref('project.group_project_user'))]
    })
    env.ref('project.menu_projects_group_stage').write({
        'groups_id': [Command.set(env.ref('project.group_project_user'))]
    })
