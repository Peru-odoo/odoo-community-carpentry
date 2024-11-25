# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['carpentry.planning.card']._rebuild_sql_view()

def uninstall_hook(cr, registry):
    """ Remove design column from carpentry project planning """
    env = api.Environment(cr, SUPERUSER_ID, {})

    domain = [('identifier_res_model', '=', 'carpentry.type')]
    env['carpentry.planning.column'].search(domain).unlink()
    env['carpentry.planning.card']._rebuild_sql_view()
