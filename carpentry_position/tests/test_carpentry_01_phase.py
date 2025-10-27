# -*- coding: utf-8 -*-

from odoo import exceptions, Command
from odoo.addons.carpentry_position.tests.test_carpentry_00_base import TestCarpentryGroup_Base

class TestCarpentryAffectationPhase(TestCarpentryGroup_Base):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_phase_01_provisioning(self):
        """ Provisioning 1 phase affectations, using
            linked `lot_ids` (like from phase's form)
        """
        self.phase.lot_ids = self.lot
        debug = False
        if debug:
            print('===test_phase_01_provisioning===')
            print('self.phase', self.phase)
            print('self.phase.affectation_ids', self.phase.affectation_ids)
            print('self.lot', self.lot)
            print('self.phase.lot_ids', self.phase.lot_ids)
        self.assertTrue(self.lot in self.phase.lot_ids)
        self.assertTrue(self.position in self.phase.position_ids)
    
    def test_phase_02_basic(self):
        """ Check basic fields of phase affectations """
        affectation = self.phase.affectation_ids
        self.assertEqual(len(affectation), 1)
        self.assertEqual(affectation.mode, 'phase')
        self.assertEqual(affectation.phase_id, self.phase)
        self.assertEqual(affectation.project_id, self.project)
        self.assertEqual(affectation.lot_id, self.lot)
        self.assertEqual(affectation.position_id, self.position)
        self.assertFalse(affectation.launch_id)
        self.assertFalse(affectation.parent_id)

    def test_phase_03_qty(self):
        """ Test usage of `quantity_affected`: empty at creation + constraint """
        affectation = self.phase.affectation_ids
        self.assertEqual(affectation.quantity_affected, 0)
        self.assertEqual(affectation.quantity_remaining_to_affect, 1)
        self.assertEqual(self.position.quantity, 1) # just to check the data
        self.assertEqual(self.position.quantity_remaining_to_affect, 1)

        try:
            affectation.quantity_affected = 1
        except exceptions.ValidationError:
            self.fail("We should be able to affected qty in the limit of position's one")
        
        self.assertEqual(affectation.quantity_remaining_to_affect, 0)
        self.assertEqual(self.position.quantity_remaining_to_affect, 0)

        with self.assertRaises(exceptions.ValidationError):
            affectation.quantity_affected = 2 # position1 has qty=1
        
        self.assertEqual(self.position.quantity_remaining_to_affect, 0)

    def test_phase_04_is_affectable(self):
        """ Try and affect the same position to another phase:
            -> ensure it's not added (because already fully affected)
        """
        # force creation of an affectation in phase2 (and clean it after)
        self.assertTrue(self.position in self.lot.position_ids)
        affectation = self.phases[1]._create_affectations(self.position)
        self.assertEqual(affectation.quantity_remaining_to_affect, 0)
        self.assertFalse(affectation.affected)
        self.assertFalse(affectation.is_affectable)
        affectation.unlink() # clean

        # try to add lot1 to phase2: it happens (doesn't happen)
        self.phases[1].lot_ids = self.lot
        self.assertTrue(self.lot in self.phases[1].lot_ids)
        self.assertTrue(self.position in self.phases[1].position_ids)
        
        # Below tests are useful if affectation's provisioning is filtered only to `remainings` ones
        # self.assertFalse(self.lot in self.phases[1].lot_ids)
        # self.assertFalse(self.position in self.phases[1].position_ids)

        # # retry with more qty in position1: it passes
        # self.position.quantity = 99
        # self.phases[1].lot_ids = self.lot
        # self.assertTrue(self.lot in self.phases[1].lot_ids)
        # self.assertTrue(self.position in self.phases[1].position_ids)
    
    # #===== Advanced provisioning =====#
    def test_phase_05a_cascade_position_create(self):
        """ Create a new position: it should cascade to related phases """
        self._create_new_position()
        self.assertTrue(self.new_position in self.phase.position_ids)

    def test_phase_05b_cascade_position_void(self):
        """ Removing position's qty: position's affectations should delete from the phase """
        self.new_position.quantity = 0
        self.assertFalse(self.new_position in self.phase.position_ids)

    def test_phase_05c_cascade_position_change_qty(self):
        """ Setting back position's qty: the position should cascade again to the phase """
        self.new_position.quantity = 10
        self.assertTrue(self.new_position in self.phase.position_ids)
    
    def test_phase_06_position_lot_change(self):
        """ Test change of position's `lot_id` """
        self._reset_affectations()
        self.assertTrue(self.lot in self.phase.lot_ids)

        self.lot.position_ids.lot_id = self.lots[2]
        self.assertFalse(self.lot    in self.phase.lot_ids)
        self.assertTrue(self.lots[2] in self.phase.lot_ids)
    
    def test_phase_07_provisioning_removal_complex(self):
        """ Remove lot1 and add lot2 in the same time => lot2 should be kept """
        # reset initial state
        self._reset_affectations()
        self.launchs.unlink() # unlink else it raises

        # remove 2 last lots => should keep only 1st
        self.phase.lot_ids = [Command.unlink(self.lots[1].id), Command.unlink(self.lots[2].id)]
        self.assertEqual(self.phase.lot_ids, self.lot)

        # unselect 1st lot, add 2nd lot => should keep only lot2
        self.positions[2].lot_id = self.lots[1] # lot2
        self.phase.lot_ids = [Command.unlink(self.lot.id), Command.link(self.lots[1].id)]
        self.assertEqual(self.phase.affectation_ids.lot_id, self.lots[1])
    
    # #===== Other =====#
    def test_phase_08_active(self):
        self.phase.toggle_active()
        self.assertFalse(
            all(self.phase.with_context(active_test=False).affectation_ids.mapped('active'))
        )
    
    def test_phase_09_convert_to_launch(self):
        self.launchs.unlink()
        res = self.phases[1].convert_to_launch()

        launch_id = res['domain'][0][2][0]
        launch = self.project.launch_ids.browse(launch_id)
        self.assertEqual(launch.name, self.phases[1].name)
