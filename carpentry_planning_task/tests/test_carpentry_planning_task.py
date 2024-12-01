# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command, tools
from odoo.tests import common, Form
from odoo.addons.carpentry_planning.tests.test_carpentry_planning import TestCarpentryPlanning

class TestCarpentryPlanningTask(TestCarpentryPlanning):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Task Stages
        cls.Stage = cls.env['project.task.type']
        cls.stage_open = cls.Stage.create({
            'name': 'In Progress Test 1',
            'project_ids': [Command.set(cls.project.ids)]
        })
        cls.stage_close = cls.stage_open.copy({'name': 'Done Test 1', 'fold': True})

        # Task
        cls.Task = cls.env['project.task']
        cls.task = cls.Task.create({'name': 'Test Task 1', 'project_id': cls.project.id})

    def test_02_task_onchange_date_end_deadline_late(self):
        """ 1. `date_deadline` is 1 week ago => test if task is late
            2. user set `date_end` => test if task is done
        """
        with Form(self.task) as f:
            f.date_deadline = tools.date_utils.subtract(fields.Datetime.today(), weeks=1)
            f.date_end = fields.Datetime.today()
        self.assertTrue(self.task.is_late)
        self.assertTrue(self.task.is_closed)
        self.assertEqual(self.task.kanban_state, 'done')

    def test_04_task_open_form(self):
        self.assertTrue(self.task.action_open_planning_task_form().get('res_id'), self.task.id)


    #===== carpentry.planning.task =====#
    def test_05_planning_search_read_extended(self):
        """ Test trick of appending fake task fields to `carpentry_planning_column.read_group` result
            Reminder: if `search_read` don't find a domain part with `launch_ids`, it returns []
        """
        res = self.Card.search_read(
            domain=[('launch_ids', '=', self.project.launch_ids.ids[0])],
            fields=['res_id'],
        )
        self.assertTrue(len(res))
        
        fields_list = self.Card._get_task_fields_list()
        self.assertTrue(all([field in res[0] for field in fields_list]))

    def test_06_planning_action_open_task(self):
        cards = self.Card.search([('launch_ids', '=', self.project.launch_ids.ids[0])])
        card = fields.first(cards).with_context({
            'project_id': self.project.id,
            'launch_id': self.project.launch_ids[0].id,
        })
        self.assertEqual(card.action_open_tasks().get('name'), card.display_name)
