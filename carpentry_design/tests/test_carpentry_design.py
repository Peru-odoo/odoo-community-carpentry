# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command, tools
from odoo.tests import common, Form
from odoo.addons.carpentry_position.tests.test_carpentry_position import TestCarpentryPosition

from datetime import datetime, timedelta

class TestCarpentryDesign(TestCarpentryPosition):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.plan_set = cls.env['carpentry.plan.set'].create([{
            'name': 'Plan Set Test 01',
            'project_id': cls.project.id,
            'launch_ids': [Command.set(cls.project.launch_ids.ids)],
            'plan_release_ids': [Command.create({'name': x}) for x in ['Test A', 'Test B']]
        }])
        cls.release1, cls.release2 = cls.plan_set.plan_release_ids


    #===== project.project =====#
    def test_01_project_plan_set_count(self):
        self.assertEqual(self.project.plan_set_count, 1)
    
    #===== carpentry.plan.release =====#
    def test_02_plan_release_week(self):
        date_ref = datetime(2024, 1, 1)
        self.release2.date_visa_feedback = date_ref + timedelta(days=7)
        self.assertEqual(
            self.release2.week_visa_feedback,
            date_ref.isocalendar().week + 1
        )
    