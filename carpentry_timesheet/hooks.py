# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api

def post_init_hook(cr, registry):
    _rebuild_budget_expense(cr)

def uninstall_hook(cr, registry):
    _rebuild_budget_expense(cr)

def _rebuild_budget_expense(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['carpentry.budget.expense.history'].init()
    env['carpentry.budget.expense'].init()
    env['carpentry.budget.expense.distributed'].init()
    env['carpentry.budget.project'].init()
