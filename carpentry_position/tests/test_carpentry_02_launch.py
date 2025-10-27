# -*- coding: utf-8 -*-

from odoo import exceptions, Command, fields
from odoo.addons.carpentry_position.tests.test_carpentry_00_base import TestCarpentryGroup_Base

class TestCarpentryAffectationLaunch(TestCarpentryGroup_Base):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_launch_01_provisioning(self):
        """ Test `_inverse_phase_ids` of launchs & phases:
            don't create launch affectation if phases' affectations qty == 0
        """
        self.launchs.affectation_ids.unlink()
        self.phases.affectation_ids.unlink()
        self.phase.lot_ids = self.lot
        self.launch.phase_ids = self.phase

        # for now, phases cannot be affected to launch because phase's affectation is qty=0
        self.assertFalse(self.launch.affectation_ids)
        self.assertFalse(self.phase in self.launch.phase_ids)
        self.assertFalse(self.position in self.launch.position_ids)

    def test_launch_02_provisioning_phase_qty(self):
        """ Ensure writing's qty of phase affectations
            creates (cascade) well the children launch affectations
        """
        self.phase.affectation_ids.quantity_affected = 1
        self.launch.phase_ids = self.phase
        self.assertTrue(self.phase in self.launch.phase_ids)
        self.assertTrue(self.position in self.launch.position_ids)

    def test_launch_03_basic(self):
        """ Check basic fields of launchs affectations """
        affectation = self.launch.affectation_ids
        phase_affectation = self.phase.affectation_ids

        # check basic fields
        self.assertEqual(len(affectation), 1)
        self.assertEqual(affectation.mode, 'launch')
        self.assertEqual(affectation.launch_id, self.launch)
        self.assertEqual(affectation.phase_id, self.phase)
        self.assertEqual(affectation.project_id, self.project)
        self.assertEqual(affectation.parent_id, phase_affectation)
        self.assertEqual(affectation.position_id, self.position)
        self.assertEqual(affectation.sequence_position, self.position.sequence)
        self.assertEqual(affectation.quantity_affected, phase_affectation.quantity_affected)

    def test_launch_04_affected(self):
        """ Test usage of `affected`: False at creation + constraint """
        affectation = self.launch.affectation_ids
        self.assertFalse(affectation.affected)

        try:
            self.launch.button_affect_all_positions()
        except exceptions.ValidationError:
            self.fail("We should be able to affect the affectation to the launch")
        
        sibling = self.launchs[1]._create_affectations(affectation.parent_id)
        # peaceful way
        try:
            self.launch.button_affect_all_positions()
        except exceptions.ValidationError:
            self.fail("The button should skip non-affectable affectations")
        # force it
        with self.assertRaises(exceptions.ValidationError):
            sibling.affected = True
        sibling.unlink() # clean for next test

    def test_launch_05_is_affectable(self):
        """ Try and affect the same position to another launch:
            -> ensure it's not added (because already fully affected)
        """
        # bypass _inverse and force the creation of position1's
        # affectation in launch2 (and clean it after)
        affectation = self.launchs[1]._create_affectations(
            self.launch.affectation_ids.parent_id
        )
        self.assertFalse(affectation.is_affectable) # like "ok it's already affected in launch1"
        affectation.unlink()
        
        # Useful only if `_get_filter_remaining_affectations` is used without `provisioning` (e.g. always False)
        # self.assertEqual(self.position.quantity_remaining_to_affect, 0) # state: position1 is fully affected (in phase1)
        # # test: try to add position1 in launch2
        # self.launchs[1].phase_ids = self.phase
        # # expected result: position1 is not being added, because already fully affected
        # self.assertFalse(self.launchs[1].affectation_ids)

        # switch position1 from launch1 to launch2 (normally)
        affectation = self.launch.affectation_ids
        self.assertTrue(affectation.is_affectable) # silly test with no siblings, just to check
        affectation.affected = False
        self.assertTrue(affectation.is_affectable)
        self.launchs[1].phase_ids = self.phase
        self.assertTrue(self.phase in self.launchs[1].phase_ids)

    #===== Advanced provisioning =====#
    def test_launch_06_phase_affectation_cascade_chain(self):
        """ Ensure affectation cascade from phase to launch. Example:
            - launch1 is linked to phase1
            => setting a new_position's affected qty to phase1 > 0
            should create launch's affected (unaffected yet)
        """
        # initial state
        self._reset_affectations()
        self._create_new_position() # on lot1 => added to phase1
        new_affectation = self.new_position.affectation_ids
        self.assertEqual(new_affectation.phase_id, self.phase) # just to ensure initial state data

        # launch1 is already linked to phase1 => setting new_position's qty_affected in phase1
        # should create empty affectation of new_position in launch1
        self.assertTrue(self.phase in self.launch.phase_ids)
        new_affectation.quantity_affected = 1
        self.assertTrue(self.new_position in self.launch.affectation_ids.position_id)

    def test_launch_07_phase_affectation_cascade_removal(self):
        """ Update phase affectation qty, or removal:
            - 0 should be prevented if *affected* children launch affectation
            - else, it should cascade-delete/create launch affectation
        """
        # initial state
        self._reset_affectations()
        self.assertTrue(all(self.launch.affectation_ids.mapped('affected'))) # there are launch affectations, being affected
        
        # can't put 0 if children launch affectation
        with self.assertRaises(exceptions.ValidationError):
            self.phase.affectation_ids.quantity_affected = 0
        # can't unlink phase affectation
        with self.assertRaises(exceptions.ValidationError):
            affectation = fields.first(self.phase.affectation_ids)
            affectation.unlink()
        
        # *CAN* put 0 if no *affected* children affectation
        self.launchs.affectation_ids.affected = False
        try:
            self.phases.affectation_ids.quantity_affected = 0
        except:
            self.fail('Should be OK to set qty to 0 if no children affected launch affectations')
        self.assertFalse(self.launchs.affectation_ids)
        
        # *CAN* unlink phase affectation if no *affected* children affectations
        self.phases.affectation_ids.quantity_affected = 1 # re-set some launch affectations
        self.launch.phase_ids = self.phases # created by unaffected
        try:
            self.phases.affectation_ids.unlink()
        except:
            self.fail('Should be OK to unlink phase affectation')
        self.assertFalse(self.launch.affectation_ids)

    # #===== Other =====#
    def test_launch_08_sequences(self):
        self._reset_affectations()

        """ Test change of lot/phase, phase/launch, position's sequence """
        self.assertEqual(self.phase.sequence, 1)
        self.assertEqual(self.phases[2].sequence, 3)

        self.phase.sequence = 99
        self.assertEqual(set(self.phase.affectation_ids.mapped('sequence_group')), {99})
        self.assertEqual(set(self.launch.affectation_ids.mapped('sequence_parent_group')), {99})
