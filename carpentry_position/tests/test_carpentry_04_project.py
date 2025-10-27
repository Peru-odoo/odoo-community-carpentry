# -*- coding: utf-8 -*-

from odoo import exceptions, _
from odoo.addons.carpentry_position.tests.test_carpentry_00_base import TestCarpentryGroup_Base

class TestCarpentryAffectationProject(TestCarpentryGroup_Base):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_unlink_cascade(self):
        self._quick_affect()
        try:
            self.project.unlink()
        except:
            self.fail("We should be able to unlink the project even with affectations")

    def test_02_position_fully_affected(self):
        self._create_project('Project1')

        # none affectations
        self.assertFalse(self.project.position_fully_affected)
        
        # partial affectations
        self.phase.lot_ids = self.lot
        self.assertFalse(self.project.position_fully_affected)
        
        # all affectations
        self._quick_affect()
        self.assertTrue(self.project.position_fully_affected)

    def test_03_position_count(self):
        self.assertEqual(self.project.position_count, len(self.positions))
        self.assertEqual(self.lot.position_count, 1)
