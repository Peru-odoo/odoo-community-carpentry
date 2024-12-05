# -*- coding: utf-8 -*-

from odoo import Command, exceptions, fields
from odoo.tests.common import Form, TransactionCase

from odoo.addons.project_budget_timesheet.tests.test_project_budget_timesheet import TestProjectBudgetTimesheet

class TestCarpentryTimesheet(TestProjectBudgetTimesheet):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.project.privacy_visibility = 'portal'
        cls.user_employee = cls.env['res.users'].create({
            'name': 'User Employee',
            'login': 'user_employee',
            'email': 'useremployee@test.com',
            'groups_id': [(6, 0, [cls.env.ref('hr_timesheet.group_hr_timesheet_user').id])],
        })
        cls.empl_employee = cls.env['hr.employee'].create({
            'name': 'User Empl Employee',
            'user_id': cls.user_employee.id,
        })

        cls.Timesheet = cls.env['account.analytic.line']

    #===== account.analytic.account =====#
    # def test_01_analytic_task_timesheetable(self):
    #     """ Test computation of computed boolean `timesheetable` on analytic.account """
    #     self.assertTrue(self.analytic.timesheetable)
    #     self.assertTrue(self.task1.allow_timesheets)
    
    #===== project.task =====#
    def test_02_task_perf_compute(self):
        """ Test computed fields `progress_viewed` and `performance` """
        # log some timesheet on task 1
        timesheet1 = self.Timesheet.with_user(self.user_employee).create({
            'project_id': self.project.id,
            'task_id': self.task1.id,
            'name': 'my first timesheet',
            'unit_amount': 4,
        })
        # yet, `progress_reviewed` follows `progress` and no perf
        self.assertEqual(self.task1.progress, self.task1.progress_reviewed)
        self.assertFalse(self.task1.performance)

        # Close task1
        self.task1.stage_id = self.env['project.task.type'].create({
            'name': 'Stage Done 01',
            'fold': True,
            'project_ids': [Command.set(self.task1.project_id.ids)]
        })
        self.assertEqual(self.task1.progress_reviewed, 100)

        same_sign = self.task1.performance * (self.task1.planned_hours - self.task1.effective_hours) > 0
        self.assertTrue(same_sign)
