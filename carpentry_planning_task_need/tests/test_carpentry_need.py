# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command, tools
from odoo.tests import common, Form

from odoo.addons.carpentry_planning_task_type.tests.test_cptry_task_type import TestCarpentryPlanningTaskType
from odoo.addons.carpentry_planning.tests.test_carpentry_planning import TestCarpentryPlanning
from odoo.addons.carpentry_planning_task_need.models.project_task import XML_ID_NEED

from datetime import date, timedelta

class TestCarpentryPlanningTaskNeed(TestCarpentryPlanning, TestCarpentryPlanningTaskType):

    @classmethod
    def setUpClass(cls):
        super(TestCarpentryPlanningTaskNeed, cls).setUpClass()
        
        # Task Type for Need
        cls.type_need_section = cls.Type.create({
            'name': 'Section of Need Test 1 (like : "Method")',
            'parent_id': cls.env.ref(XML_ID_NEED).id,
            'task_ok': True
        })
        cls.type_need_child = cls.Type.create({
            'name': 'Child Type Need Test 1 (like: "Debit")',
            'parent_id': cls.type_need_section.id,
            'task_ok': True
        })
        # Create another section of needs
        cls.type_need_section2 = cls.type_need_section.copy({
            'name': 'Section of Need Test 2 (like : "Construction")'
        })
        cls.type_need_child2 = cls.type_need_child.copy({
            'name': 'Child Type Need Test 2 (like: "Reception")',
            'parent_id': cls.type_need_section2.id,
        })

        # Planning Column
        cls.PlanningColumn = cls.PlanningColumn.with_context(no_test_mirroring_column_id=False)
        cls.column_need = cls.PlanningColumn.create({
            'name': 'Column Need Test 1',
            'res_model_id': cls.mapped_model_ids['project.task'].id,
            'identifier_res_id': cls.type_need_section.id,
            'identifier_res_model_id': cls.mapped_model_ids['project.task'].id,
            'sticky': False,
            'column_id_need_date': cls.column.id
        })

        # Need & Need Family
        cls.NeedFamily = cls.env['carpentry.need.family'].with_context(default_project_id = cls.project.id)
        cls.need_family = cls.NeedFamily.create([{
            'name': 'Need Family Test 1',
            'need_ids': [Command.create({
                'name': 'Need Test 1',
                'deadline_week_offset': 4,
                'type_id': cls.type_need_child.id
            })]
        }])

        # Affectation of Need Family with Launchs => tasks creation
        cls.need_family.launch_ids = cls.project.launch_ids # 3 launches
    

    #===== carpentry.need.family =====#
    def test_01_need_family_unique_parent_type_id(self):
        """ Test prevention of mixing different `parent_type_id` in same need family """
        with self.assertRaises(exceptions.ValidationError):
            self.need_family.need_ids = [Command.create({
                'name': 'Need Test Other Family',
                'deadline_week_offset': 4,
                'type_id': self.type_need_child2.id
            })]

    def test_02_need_family_reconcile(self):
        """ Test task/need synchro: when affecting need family to launch, this should create task """
        # 1 need in 1 family, affected to 3 launches => 3 tasks
        self._compare_need_task_count(3)

        # same need in another family, affected to same launches => still same 3 tasks, not touched
        need_family2 = self.need_family.copy({
            'name': 'Need Family Test 2',
            'need_ids': [Command.set(self.need_family.need_ids.ids)],
            'launch_ids': [Command.set(self.project.launch_ids.ids)],
        })
        self._compare_need_task_count(3)

        # unaffect 1 launch => 2 tasks
        self.need_family.launch_ids = [Command.unlink(fields.first(self.project.launch_ids).id)]
        need_family2.launch_ids = [Command.unlink(fields.first(self.project.launch_ids).id)]
        self._compare_need_task_count(2)

    def _compare_need_task_count(self, expected_count):
        domain = [('deadline_week_offset', '!=', False)]
        task_count = self.env['project.task'].search_count(domain)

        self.assertEqual(expected_count, task_count)

    #===== carpentry.need =====#
    def test_03_need_prevent_delete(self):
        with self.assertRaises(exceptions.ValidationError):
            self.need_family.need_ids.unlink()

    #===== project.type =====#
    def test_04_type_column_id(self):
        self.assertEqual(self.type_need_child.column_id, self.column_need)

    #===== carpentry.planning =====#
    def test_05_card_action_open_need(self):
        domain = [('launch_ids', '=', self.project.launch_ids.ids), ('column_id', '=', self.column_need.id)]
        card_ids = self.Card.search(domain)
        card = fields.first(card_ids).with_context({
            'project_id': self.project.id,
            'launch_id': self.project.launch_ids[0].id,
        })

        action = card.action_open_tasks()
        self.assertEqual(self.env.ref(XML_ID_NEED).id, action.get('context').get('default_parent_type_id'))

    #===== project.task =====#
    def test_06_task(self):
        task = self.env['project.task'].search([('deadline_week_offset', '!=', False)])[0]
        
        # Computed deadline
        prod_start = date(2024, 1, 31)
        task.lauch_id.milestone_ids.filtered(lambda x: x.type =='start').date = prod_start
        self.assertEqual(
            task.date_deadline,
            prod_start - timedelta(weeks=4)
        )
        
        # Unlink should be prevented
        with self.assertRaises(exceptions.ValidationError):
            task.unlink()

    def test_07_task_standalone(self):
        task = self.env['project.task'].create({
            'name': 'Test Standalone Need 01',
            'launch_id': self.launch.id,
            'type_id': self.type_need_child.id
        })

        # Test computation of `res_card_id` and `res_card_model_id` for standalone needs
        self.assertEqual(task.card_res_model, 'project.type')
        self.assertEqual(task.card_res_id, self.type_need_child.id)

        # standalone can be deleted
        try:
            task.unlink()
        except:
            self.fail('Manual need should be deletable')
