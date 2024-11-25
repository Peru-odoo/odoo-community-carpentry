
Document the need of `hook` and call to `_rebuild_sql_view()`

# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api

def _rebuild_sql_view(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['carpentry.planning.card']._rebuild_sql_view()

def post_init_hook(cr, registry):
    _rebuild_sql_view(cr)

def uninstall_hook(cr, registry):
    _rebuild_sql_view(cr)

manifest:
    'post_init_hook': 'post_init_hook', # rebuild sql view
    'uninstall_hook': 'uninstall_hook',
