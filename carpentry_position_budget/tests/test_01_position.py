# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command
from odoo.tests import common, Form

from .test_00_position_budget_base import TestCarpentryPositionBudget_Base

class TestCarpentryPositionBudget_Position(TestCarpentryPositionBudget_Base):

    BUDGET_INSTALL = 10.0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # duplicate position with some budget
        cls.position_duplicate = cls.position.copy({'quantity': 2})
        cls.position_duplicate.write({'name': cls.position.name})
        cls.position_duplicate.position_budget_ids = [Command.create({
            'analytic_account_id': cls.aac_install.id,
            'amount': cls.BUDGET_INSTALL
        })]

        # merge wizard
        cls.Wizard = cls.env['carpentry.position.merge.wizard']
        f = Form(cls.Wizard.with_context(active_ids=[cls.position.id]))
        cls.wizard = f.save()


    #===== carpentry.position =====#
    def test_01_position_display_name(self):
        display_name = self.position.with_context(merge_wizard=True).display_name
        self.assertTrue(self.lot.name in display_name)
    
    def test_02_position_warning_name(self):
        self.assertTrue(self.position.warning_name)
        self.assertTrue(self.position_duplicate.warning_name)
        self.assertFalse(self.project.position_ids[2].warning_name)
    

    #===== carpentry.position.merge.wizard =====#
    def test_03_merge_default_get_button(self):
        """ Test default value in 1st flow: 'Merge' button on tree row """
        self.assertEqual(
            set(self.wizard.position_ids_to_merge.ids),
            set((self.position_duplicate | self.position).ids)
        )
        self.assertEqual(self.wizard.position_id_target.id, self.position.id)
    
    def test_04_merge_default_active_ids(self):
        """ Test default value in 2nd flow: several positions selected
            on tree's checkbox, then "Merge" top action
        """
        f = Form(self.Wizard.with_context(active_ids=self.project.position_ids.ids))
        f.position_id_target = self.position
        wizard2 = f.save()

        self.assertEqual(wizard2.position_ids_to_merge.ids, self.project.position_ids.ids)
    
    def test_05_merge_button_logic(self):
        """ Test confirmation of merge wizard button """
        self.position.quantity = 1
        self.position_duplicate.quantity = 2
        self.position.position_budget_ids.unlink() # 0 budget for target
        self.wizard.button_merge()

        # Qty: should sum & budget: should weighted-avg
        self.assertEqual(self.position.quantity, 3)
        self.assertEqual(round(self.position.budget_install, 2), round((0.0 * 1 + self.BUDGET_INSTALL * 2) / 3, 2))
