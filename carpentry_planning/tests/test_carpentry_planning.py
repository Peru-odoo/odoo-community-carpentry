# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command, tools
from odoo.tests import common, Form
from odoo.addons.carpentry_position.tests.test_carpentry_position import TestCarpentryPosition

class TestCarpentryPlanning(TestCarpentryPosition):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        model_ids = cls.env['ir.model'].search([])
        cls.mapped_model_ids = {x.model: x for x in model_ids}

        cls.PlanningColumn = cls.env['carpentry.planning.column'].with_context(no_test_mirroring_column_id=True)
        cls.column = cls.PlanningColumn.create({
            'name': 'Column Test',
            'res_model_id': cls.mapped_model_ids.get('project.project').id,
            'sticky': True,
            'icon': 'fa-xxx'
        })

        cls.Card = cls.env['carpentry.planning.card']

        MilestoneType = cls.env['carpentry.planning.milestone.type']
        cls.milestone_type = MilestoneType.create([{
            'name': 'Milestone Type Test - Date start 1',
            'column_id': cls.column.id,
            'type': 'start'
        }, {
            'name': 'Milestone Type Test - Date end 1',
            'column_id': cls.column.id,
            'type': 'end'
        }])


    #===== carpentry.planning.column =====#
    def test_01_column_identifier_ref(self):
        """ Test `identifier_ref` logic and constrain """
        # Constrain: another column on same model should raise,
        # even with an identifier on the new column (because of column1)
        with self.assertRaises(exceptions.ValidationError):
            self.column.with_context(no_test_mirroring_column_id=True).copy({
                'name': 'Column Test 02',
                'identifier_ref': '{},{}' . format('project.project', self.project.id)
            })

        # Just ensure of `identifier_ref` inverse logic
        self.column.identifier_ref = '%s,%s' % (self.project._name, self.project.id)
        self.assertEqual(self.column.identifier_res_id, self.project.id)
        self.assertFalse(self.column.identifier_required)
        

    def test_02_column_headers(self):
        launch_id_ = fields.first(self.project.launch_ids).id
        columns_headers = self.column.get_headers_data(launch_id_)
        self.assertEqual(
            columns_headers.get(self.column.id).get('icon'),
            self.column.icon
        )

    #===== carpentry.planning.card =====#
    def test_03_card_rebuild_sql_view(self):
        self.column.with_context(test_mode=True).sequence = 12 # `sequence` is a field triggering the rebuild
        card_ids = self.Card.search([])
        self.assertTrue(self.project.id in card_ids.mapped('res_id'))

    def test_04_card_read_group(self):
        """ `read_group` without `launch_ids` in domain results empty """
        # no `launch_ids`: should be empty
        kwargs = {'domain': [], 'fields': ['res_id:array_agg'], 'groupby': ['column_id']}
        self.assertFalse(self.Card.read_group(**kwargs))

        # `launch_ids`: should result something (since our column is `sticky`)
        kwargs['domain'] = [('launch_ids', '=', True)]
        self.assertTrue(self.Card.read_group(**kwargs))

    def test_05_card_real_record(self):
        card_ids = self.Card.search([])
        card_id = card_ids.filtered(lambda x: x.res_id == self.project.id)
        self.assertEqual(card_id._real_record_one(), self.project)
        self.assertEqual(card_id.display_name, self.project.display_name)


    #===== carpentry.planning.milestone, .types & launches =====#
    def test_06_milestone_type_prefill(self):
        """ Test if milestones auto-created in all launches in base """
        self.assertTrue(self.project.launch_ids.milestone_ids.ids)

        new_launch_id = fields.first(self.project.launch_ids).copy({'name': 'New Test Launch 4'})
        self.assertTrue(new_launch_id.milestone_ids.ids)
        new_launch_id.unlink() # for compatibilty in SingleTransactionCase
    
    def test_07_milestone_date_constrain(self):
        """ Test date `start` < date `end` constrain """
        milestones = self.project.launch_ids[0].milestone_ids
        milestone_start = fields.first(milestones.filtered(lambda x: x.type == 'start'))
        milestone_end = milestones.filtered(lambda x: x.type == 'end' and x.column_id == milestone_start.column_id)

        milestone_start.date = '2024-01-15'
        with self.assertRaises(exceptions.ValidationError):
            with Form(milestone_end) as f:
                f.date = '2024-01-10'
