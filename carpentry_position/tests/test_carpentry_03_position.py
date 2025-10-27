# -*- coding: utf-8 -*-

from odoo import exceptions, _
from odoo.addons.carpentry_position.tests.test_carpentry_00_base import TestCarpentryGroup_Base

class TestCarpentryPosition(TestCarpentryGroup_Base):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_state_01_phase_provisioning(self):
        """ Test position state: with provisioning but no quantity affected
            (i) let's affect 2nd lot to 1st phase (position[1].qty=2)
        """
        self.phase.lot_ids = self.lots[1]
        self.assertEqual(set(self.positions.mapped('state')), {('none')})
        self.assertEqual(self.positions[1].quantity_remaining_to_affect, 2)

    def test_01_state_02_phase_affectation(self):
        """ Test total/partial affectation in phase,
            playing with amount of position's qty affected in phases
        """
        # partial affectation on phase
        self.phase.affectation_ids.quantity_affected = 1
        self.assertEqual(self.positions[1].quantity_remaining_to_affect, 1)
        self.assertEqual(self.positions[1].state, 'warning_phase')

        # total affectation, on another phase -> feedback like partial on launch
        self.phases[1].lot_ids = self.lots[1]
        self.phases[1].affectation_ids.quantity_affected = 1
        self.assertEqual(self.positions[1].quantity_remaining_to_affect, 0)
        self.assertEqual(self.positions[1].state, 'warning_launch')

    def test_01_state_03_launch_affectation(self):
        """ Test total/partial affectation in launch """
        # still partial affectation on launch
        self.launch.phase_ids = self.phase
        self.launch.affectation_ids.affected = True
        self.assertEqual(self.positions[1].state, 'warning_launch')

        # full affectation on launch
        self.launchs[1].phase_ids = self.phases[1]
        self.launchs[1].affectation_ids.affected = True
        self.assertEqual(self.positions[1].state, 'done')

    def test_02_qty_01_constrain(self):
        """ Cannot lower quantity under affected qty in phases """
        try:
            self.positions[1].quantity = 3
        except exceptions.ValidationError:
            self.fail("We should be able to *raise* position's quantity")

        with self.assertRaises(exceptions.ValidationError):
            self.positions[1].quantity = 0 # qty of 2 is affected on phase

    def test_02_qty_02_propagate(self):
        """ Ensure position's quantity propagate to launch's `quantity_affected` """
        self.launch.position_ids.quantity = 99
        self.assertEqual(self.launch.affectation_ids.quantity_position, 99)
    
    def test_03_unlink_01_affectation_cascade(self):
        self.assertTrue(self.phase.affectation_ids.children_ids)
        try:
            self.phase.unlink()
        except exceptions.ValidationError:
            self.fail("A phase, even with children affectation, should be OK to be deleted")
    
    def test_03_unlink_02_position_cascade(self):
        self._reset_affectations()
        self.assertTrue(self.position.affectation_ids.children_ids)
        try:
            self.position.unlink()
        except exceptions.ValidationError:
            self.fail("A position, even fully affected, should be OK to be deleted ")
    
    def test_04_position_copy(self):
        last_position = self.project.position_ids[-1]
        copied_position_id = last_position.copy()
        self.assertEqual(copied_position_id.name, last_position.name + _(' (copied)'))
