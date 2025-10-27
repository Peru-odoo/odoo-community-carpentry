# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command, tools
from odoo.tests import common, Form
from odoo.addons.carpentry_position.tests.test_carpentry_00_base import TestCarpentryGroup_Base

import datetime

class TestCarpentryPlanning(TestCarpentryGroup_Base):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.PlanningColumn = cls.env['carpentry.planning.column'].with_context(no_test_mirroring_column_id=True)
        cls.column = cls.PlanningColumn.create({
            'name': 'Column Test',
            'res_model_id': cls.env['ir.model']._get_id('project.project'),
            'icon': 'fa-xxx'
        })

        cls.Card = cls.env['carpentry.planning.card']

        # Milestone Type
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

        # Milestones
        cls.milestones = cls.launch.milestone_ids
        cls.milestone_start = fields.first(
            cls.milestones.filtered(lambda x: x.type == 'start')
        )
        cls.milestone_end = cls.milestones.filtered(
            lambda x: x.type == 'end' and x.column_id == cls.milestone_start.column_id
        )

    @classmethod
    def _create_wizard(cls):
        Wizard = Form(
            cls.env['carpentry.planning.milestone.wizard'].with_context(
            default_milestone_id=cls.milestone_end.id
        ))
        return Wizard.save()

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
        kwargs['domain'] = [('launch_ids', 'in', self.project.launch_ids.ids)]
        self.assertTrue(self.Card.read_group(**kwargs))

    def test_05_card_real_record(self):
        card = self.Card.search([('res_id', '=', self.project.id)])
        self.assertEqual(card._real_record_one(), self.project)
        self.assertEqual(card.display_name, self.project.display_name)

    #===== carpentry.planning.milestone, .types & launches =====#
    def test_06_milestone_type_prefill(self):
        """ Test if milestones auto-created in all launches in base """
        self.assertTrue(self.project.launch_ids.milestone_ids.ids)

        new_launch_id = fields.first(self.project.launch_ids).copy({'name': 'New Test Launch 4'})
        self.assertTrue(new_launch_id.milestone_ids.ids)
        new_launch_id.unlink() # for compatibilty in SingleTransactionCase
    
    def test_07_milestone_date_constrain(self):
        """ Test date `start` < date `end` constrain """
        self.milestone_start.date = '2024-01-15'
        with self.assertRaises(exceptions.ValidationError):
            with Form(self.milestone_end) as f:
                f.date = '2024-01-10'

    def test_08_milestone_wizard(self):
        """ Test changing a date from the planning's wizard """
        # setup
        start, end = datetime.date(2024, 1, 1), datetime.date(2024, 1, 22) # mondays
        self.milestone_start.date, self.milestone_end.date = start, end
        # wizard to change `milestone_end`

        # Test with offset (-2 weeks)
        wizard = self._create_wizard()
        with Form(wizard) as f:
            f.offset = -2
        wizard.button_set_date()
        self.assertEqual(self.milestone_end.date,   end -   datetime.timedelta(weeks=2))
        self.assertEqual(self.milestone_start.date, start - datetime.timedelta(weeks=2))

        # Test by setting date (+3 weeks)
        wizard = self._create_wizard()
        with Form(wizard) as f:
            f.date_new = '2024-01-29'
        wizard.button_set_date()
        self.assertEqual(self.milestone_end.date,   datetime.date(2024, 1, 29))
        self.assertEqual(self.milestone_start.date, datetime.date(2024, 1, 8))

        # Test with no shift
        wizard = self._create_wizard()
        with Form(wizard) as f:
            f.shift = False
            f.date_new = '2024-02-15'
        wizard.button_set_date()
        # no change
        self.assertEqual(self.milestone_start.date, datetime.date(2024, 1, 8))
