# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command
from odoo.tests import common


class TestCarpentryPosition_Base(common.SingleTransactionCase):
    """ Dedicated class only with setup() so it can be inherited
        without running tests
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        (
            cls.project, cls.lot, cls.phase, cls.launch, cls.position
        ) = cls._create_project_with_test_data('Project Test 1')
        
        cls.Affectation = cls.env['carpentry.group.affectation']
        cls.AffectationTemp = cls.env['carpentry.group.affectation.temp']
    
    @classmethod
    def _create_project_with_test_data(self, project_name):
        Project = self.env['project.project']
        project = Project.create({'name': project_name})

        # Create 3 lots, phases, launches
        group_vals_list = [
            {'project_id': project.id, 'name': f'{project.name} - Group Test {i}'}
            for i in [1,2,3]
        ]
        lot_ids = self.env['carpentry.group.lot'].create(group_vals_list)
        phase_ids = self.env['carpentry.group.phase'].create(group_vals_list)
        launch_ids = self.env['carpentry.group.launch'].create(group_vals_list)

        # Create 3 positions, 1 per lot
        position_ids = self.env['carpentry.position'].create([
            {
                'project_id': project.id,
                'name': 'Position' + str(i),
                'quantity': i+1,
                'lot_id': lot.id
            }
            for i, lot in enumerate(project.lot_ids)
        ])

        return (
            project,
            fields.first(project.lot_ids),
            fields.first(project.phase_ids),
            fields.first(project.launch_ids),
            fields.first(project.position_ids),
        )


    # A few helper methods to play with real and temp affectations
    @classmethod
    def _write_affect(self, group_id, record_id, vals=None):
        """ Shortcut to simulate user write in `carpentry.group.affectation` """
        mapped_model_ids = group_id._get_mapped_model_ids()
        vals = group_id._get_affect_vals(mapped_model_ids, record_id, group_id) | (vals or {})
        return self.Affectation.create(vals)
    
    @classmethod
    def _clean_affectations(self, quick_affect=False):
        self.project.launch_ids.affectation_ids.unlink()
        self.project.affectation_ids.unlink()
        if quick_affect:
            self._quick_affect_all()
    
    @classmethod
    def _quick_affect_all(self):
        """ Quick-affect all position's to 1st phase & launch """
        self.phase.section_ids = [Command.set(self.project.lot_ids.ids)]
        self.launch.section_ids = [Command.set(self.project.phase_ids.ids)]



class TestCarpentryPosition(TestCarpentryPosition_Base):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()


    def test_position_copy(self):
        copied_position_id = self.position.copy()
        self.assertEqual(copied_position_id.name, self.position.name + _(' (copied)'))

    def test_project_position_count(self):
        self.assertEqual(self.project.position_count, len(self.project.position_ids))
    
    def test_display_name(self):
        """ Test specifics `display_name`: position and nested affectation """
        self._clean_affectations(quick_affect=True)

        # Position's in phase affectation
        self.assertEqual(
            self.position.with_context(display_with_suffix=True).display_name,
            "[%s] %s (%s)" % (
                self.lot.name,
                self.position.name,
                self.position.quantity
            )
        )



    def test_affectations(self):
        """ - Test real affectation, like group's form wizard (phase & launch)
            - Test shortcut affectation, like group's tree view
            (cannot test like with x2m_2d_matrix)
        """
        self._clean_affectations()

        # === 1. Phases via `affectation.temp` and x2m_2d_matrix ===
        #     0 1 2 <- phases in column (lines are positions)
        # 0 | . . .
        # 1 | 1 1 .
        # 2 | . . .

        # Simulate project's form display (phases)
        self.project._compute_affectation_ids_temp_phase()
        self.assertEqual(
            len(self.project.affectation_ids_temp_phase),
            len(self.project.phase_ids) * len(self.project.position_ids)
        )

        # Positions-to-phases tests [position2 (qty=2) on phases 1 and 2 with qty=1]
        for i in [0,1]:
            self._write_affect(self.project.phase_ids[i], self.project.position_ids[1], {'quantity_affected': 1})
        self.assertEqual(len(self.phase.affectation_ids), 1)
        self.assertEqual(self.project.position_ids[1].quantity_remaining_to_affect, 0)
        self.assertEqual(self.project.position_ids[1].state, 'warning_launch')
        self.assertEqual(self.phase.sum_quantity_affected, 1) # Phase's positions count
        self.assertEqual(self.phase.section_ids.ids, self.project.lot_ids[1].ids) # Phase' sections (lots)

        # Constrain position's: `remaining to affect`
        with self.assertRaises(exceptions.ValidationError):
            self._write_affect(self.project.phase_ids[2], self.project.position_ids[1], {'quantity_affected': 1})
        # Constrain position's: >0
        # with self.assertRaises(exceptions.ValidationError):
        #     self._write_affect(self.project.phase_ids[2], self.project.position_ids[1], {'quantity_affected': 0})
        

        # === 2. Launches via `affectation.temp` and x2m_2d_matrix ===
        #     0 1 2 <- launches in column (lines are positions-to-phases' affectations)
        # 0 | v . . (phase0-position1)
        # 1 | . v . (phase1-position1)

        # Test project's form display (launches)
        self.assertEqual(len(self.project.launch_ids), 3)
        self.assertEqual(len(self.project.phase_ids.affectation_ids), 2)
        self.assertEqual(len(self.project.affectation_ids_temp_launch), 6) # Count of cells should be 2*3=6

        # Constrain M2o-like [1st affectation to launch0]
        self._write_affect(self.launch, self.project.phase_ids.affectation_ids[0])
        with self.assertRaises(exceptions.ValidationError): 
            self._write_affect(self.project.launch_ids[1], self.project.phase_ids.affectation_ids[0])

        # Position counts & sections
        self.assertEqual(self.launch.sum_quantity_affected, 1)
        self.assertEqual(self.launch.section_ids.ids, self.phase.ids)

        # Position1: test `state` (fully affected) [2nd affectation to launch1]
        self._write_affect(self.project.launch_ids[1], self.project.phase_ids.affectation_ids[1])
        self.assertEqual(self.project.position_ids[1].state, 'done') # Position1 fully affected

        # Fake-display of Launch matrix, and verify constrains on `temp`
        self.project._compute_affectation_ids_temp_launch() 

        # === 3. Classic & shortcut affectations (to phase2) ===
        #     0 1 2
        # 0 | . . 1
        # 1 | 1 1 .
        # 2 | . 1 2 (<-- tests the mass affectation with *remaining qty*)

        # Test mass affectation of all lots to phases2 [before: 1 qty of position2 to phase1]
        self._write_affect(self.project.phase_ids[1], self.project.position_ids[2], {'quantity_affected': 1})
        self.project.phase_ids[2].section_ids = [Command.set(self.project.lot_ids.ids)]
        self.assertEqual( # position1 was already fully affected => test lot1 not related to phase2
            self.project.phase_ids[2].section_ids,
            self.project.lot_ids - self.project.lot_ids[1]
        )
        # 1 qty of position2 was affected to phase1 before shortcut => test if position2-phase2 is only with qty=2
        affectation = self.project.phase_ids[2].affectation_ids.filtered(lambda x: x.record_id == self.project.position_ids[2].id)
        self.assertEqual(affectation.quantity_affected, 0.0)

        # project's positions all affected in phases but not in launch
        self.assertFalse(self.project.position_fully_affected)

        # === 4. Shortcut affectations (to launch2) ===
        #     0 1 2
        # 0 | v . . <- no change though mass shortcut affect
        # 1 | . v . <- no change ...
        # 2 | . . v <- mass affect to launch 2
        # 3 | . . v <- ...
        # 4 | . . v <- ...
        self.project.launch_ids[2].section_ids = [Command.set(self.project.phase_ids.ids)] # launch2 shortcut with all phases
        self.assertEqual(self.project.launch_ids[2].sum_quantity_affected, 1.0) # 1 positions in launch2
        self.assertEqual( # launch2 *only* linked to phase1 and 2
            set(self.project.launch_ids[2].section_ids.ids),
            set([self.project.phase_ids[1].id, self.project.phase_ids[2].id])
        )

        # project's positions all fully affected
        # self.assertTrue(self.project.position_fully_affected)

        # Cannot remove phases affectation in there are launch's one linked to them
        with self.assertRaises(exceptions.UserError):
            self.project.phase_ids.affectation_ids.unlink()

    def test_populate_group_from_section(self):
        """ Test button 'populate group from section' """
        project, _, _, _, _ = self._create_project_with_test_data('Project test2')
        project.launch_ids.unlink()
        project.phase_ids.unlink()

        project = project.with_context(default_project_id=project.id)
        project.phase_ids.button_group_quick_create()
        project.launch_ids.button_group_quick_create()
        self.assertTrue(project.launch_ids.ids)
        # self.assertTrue(project.position_fully_affected)

    def test_sequence(self):
        """ Test update of fields `sequence`, `sec_group`, `sec_section`
            in `carpentry.group.affectation`
        """
        self._clean_affectations(quick_affect=True)

        self.assertEqual(self.project.launch_ids[2].sequence, 3)

        # Modify a group's sequence: it should propagate to its affectation & children
        self.phase.sequence = 10
        self.assertEqual(self.phase.affectation_ids.mapped('seq_group'), [10])
        self.assertEqual(self.project.launch_ids.affectation_ids.mapped('seq_section'), [10])

        # Modify a position's sequence: it should propagate to its affectation & children
        self.position.sequence = 20
        affectations = self.project.affectation_ids.filtered(lambda x: x.position_id == self.position)
        self.assertEqual(affectations.sequence('section'), [20])

    
    def test_inverse_temp(self):
        """ Test writing in real `affectation` from x2m_2d_matrix of affectation temp """
        self._clean_affectations()

        # simulate user input in x2m_2d_matrix [phase0, position0: qty=1]
        self.project._compute_affectation_ids_temp_phase()
        domain = self.phase._get_domain_affect(group2_ids=self.position)
        temp_id = self.env['carpentry.group.affectation.temp'].search(domain)
        self.project.write({
            'affectation_ids_temp_phase': [Command.update(temp_id.id, {'quantity_affected': 1})]
        })

        # position0 should be well affected to phase0, in real
        self.assertEqual(
            self.project.phase_ids.affectation_ids.record_ref.ids,
            [self.position.id]
        )
