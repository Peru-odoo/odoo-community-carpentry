# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command
from odoo.tests import common, Form

from odoo.tools import file_open
import base64

from .test_00_position_budget_base import TestCarpentryPositionBudget_Base

class TestCarpentryPositionBudget_Import(TestCarpentryPositionBudget_Base):

    BUDGET_ALUMINIUM = 100.0 # euros
    budget_production = 20.0 # hours
    budget_installation = 10.0 # hours

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Groups (holding permissions)
        group_project_user = self.env.ref('project.group_project_user')
        group_project_user_global = self.env.ref('project_role_visibility.group_project_user_global')

        # User project standard
        cls.user_project = self.env['res.users'].create({
            'name': 'User Project 01',
            'login': 'user_project_01'
        })
        group_project_user.users = [Command.link(user_project.id)]
        # User project global
        cls.user_project_global = self.env['res.users'].create({
            'name': 'User Project Global 01',
            'login': 'user_project_global_01'
        })
        group_project_user_global.users = [Command.link(user_project_global.id)]


    def test_01_security_access_rules_standard_user(self):
        """ Standard user cannot see budget without a role on the project """
        with self.assertRaises(exceptions.AccessError):
            self.budget.with_user(user_project).check_access("read")
    
    def test_02_security_access_rules_global_user(self):
        """ User (all projects) should see all project budget, even with no role """
        try:
            self.budget.with_user(user_project_global).check_access("read")
        except:
            self.fail('User (all projects) should see all project budget')
