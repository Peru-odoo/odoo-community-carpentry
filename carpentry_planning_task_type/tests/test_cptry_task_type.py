# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command, tools
from odoo.tests import common, Form
from odoo.addons.carpentry_planning_task_type.models.project_task import (
    XML_ID_INSTRUCTION, XML_ID_MILESTONE, XML_ID_MEETING
)

class TestCarpentryPlanningTaskType(common.SingleTransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Project
        cls.project = cls.env['project.project'].create({"name": "Project test 1"})
        
        # User
        cls.user = cls.env['res.users'].create({"name": "User test ", "login": "user_test_1",})

        # Task Types
        cls.Task = cls.env['project.task']
        cls.Type = cls.env['project.type']
        cls.type_meeting, cls.type_milestone, cls.type_instruction = cls.Type.create([{
            'name': 'Child Type Meeting Test 1',
            'parent_id': cls.env.ref(XML_ID_MEETING).id,
            'task_ok': True
        }, {
            'name': 'Child Type Milestone Test 1',
            'parent_id': cls.env.ref(XML_ID_MILESTONE).id,
            'task_ok': True
        }, {
            'name': 'Child Type Instruction Test 1',
            'parent_id': cls.env.ref(XML_ID_INSTRUCTION).id,
            'task_ok': True
        }])

        # Assignation <-> Role <-> Type
        cls.role = cls.env['project.role'].create({'name': 'Role Meeting Test 1'})
        cls.type_meeting.role_id = cls.role
        cls.env['project.assignment'].create({
            "project_id": cls.project.id,
            "role_id": cls.role.id,
            "user_id": cls.user.id,
        })

        # Task: creation with `default_root_type_id` in context for test task_01
        cls.Task = cls.Task.with_context(default_project_id = cls.project.id)
        # meeting
        cls.Task_meeting = cls.Task.with_context(default_root_type_id = cls.env.ref(XML_ID_MEETING).id)
        cls.task_meeting =  cls.Task_meeting.create([{'name': 'Task Meeting Test 1'}])
        # milestone
        cls.Task_milestone = cls.Task.with_context(default_root_type_id = cls.env.ref(XML_ID_MILESTONE).id)
        cls.task_milestone =  cls.Task_milestone.create([{'name': 'Task Milestone Test 1',}])
        # instruction
        cls.Task_instruction = cls.Task.with_context(default_root_type_id = cls.env.ref(XML_ID_INSTRUCTION).id)
        cls.task_instruction =  cls.Task_instruction.create([{'name': 'Task Instruction Test 1'}])


    #===== project.task =====#
    def test_01_task_default_type(self):
        """ Test default type choice as per `root_type_id` logic """
        self.assertEqual(self.task_meeting.type_id, self.type_meeting)

        self.assertEqual(self.task_meeting.root_type_id, self.env.ref(XML_ID_MEETING))
        self.assertEqual(self.task_instruction.root_type_id, self.env.ref(XML_ID_INSTRUCTION))
        self.assertEqual(self.task_milestone.root_type_id, self.env.ref(XML_ID_MILESTONE))
    
    def test_02_task_default_name_required(self):
        self.assertTrue(self.task_instruction.name_required)
    
    def test_03_task_default_assignee(self):
        """ Test default assignee in `default_get` """
        self.assertTrue(self.user.id in self.task_meeting.user_ids.ids)
    
    def test_04_task_read_group_by_type(self):
        """ Test that kanban view renders all types per root_type_id """
        self.type_milestone.copy({'name': 'Type Milestone Test 2'})
        
        # Kanban browsing result
        rg_result = self.Task.read_group(
            domain=[('id', '=', self.task_milestone.id)],
            fields=['id:array_agg'],
            groupby=['type_id']
        )
        type_ids_ = [x['type_id'][0] for x in rg_result]
        
        # All expected types (research)
        domain = [('root_type_id', '=', self.env.ref(XML_ID_MILESTONE).id), ('task_ok', '=', True)]
        self.assertEqual(type_ids_, self.Type.search(domain).ids)

    # def test_05_task_display_name(self):
    #     self.assertEqual(
    #         self.task_meeting.display_name, 
    #         f'{self.type_meeting.name} - {self.task_meeting.name}'
    #     )
    
    #===== special tasks =====#
    def test_06_task_meeting(self):
        self.task_meeting.message_post(body='First message', message_type='comment')
        self.task_meeting.message_post(body='Second message', message_type='comment')
        self.assertEqual(self.task_meeting.count_message_ids, 2)
        

    #===== project.type =====#
    def test_07_type_cannot_delete_root(self):
        with self.assertRaises(exceptions.ValidationError):
            self.env.ref(XML_ID_MEETING).unlink()


    #===== project.project =====#
    def test_08_project_planning_dashboard(self):
        data = self.task_meeting.project_id.get_planning_dashboard_data()
        self.assertTrue(len(data.get('meetings')))
