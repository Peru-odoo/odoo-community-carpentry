# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command
from odoo.tests import common


class TestCarpentryGroup_Base(common.SingleTransactionCase):
    """ Class that only creates test data in setup(),
         so it can be inherited without running tests
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Data creation
        cls._create_project('Project1')
    
    @classmethod
    def _create_project(cls, project_name):
        """ Creates 1 test project with data sample:
            - 3 lots
            - 3 phases
            - 3 launchs
            - 3 positions
            :return: 1st item of each
        """
        cls.Project = cls.env['project.project']
        cls.project = cls.Project.create({'name': project_name})

        # Create 3 lots, phases, launches
        for group in ('Lot', 'Phase', 'Launch'):
            vals_list = [
                {'project_id': cls.project.id, 'name': group + str(i)}
                for i in [1,2,3]
            ]
            cls.env['carpentry.group.' + group.lower()].create(vals_list)

        # Create 3 positions, 1 per lot
        cls.env['carpentry.position'].create([
            {
                'project_id': cls.project.id,
                'name': 'Position' + str(i),
                'quantity': i,
                'lot_id': lot.id
            }
            for i, lot in enumerate(cls.project.lot_ids, start=1)
        ])

        # store in cls
        cls.lots      = cls.project.lot_ids
        cls.phases    = cls.project.phase_ids
        cls.launchs   = cls.project.launch_ids
        cls.positions = cls.project.position_ids

        # shortcuts (firsts of the 3)
        cls.lot = fields.first(cls.lots)
        cls.phase = fields.first(cls.phases)
        cls.launch = fields.first(cls.launchs)
        cls.position = fields.first(cls.positions)

    # Helper methods to handle affectations
    @classmethod
    def _quick_affect(cls):
        """ Quick-affect all position's to 1st phase & launch """
        cls.phase.lot_ids = cls.project.lot_ids
        for affectation in cls.phase.affectation_ids:
            affectation.quantity_affected = affectation.quantity_remaining_to_affect

        cls.launch.phase_ids = cls.project.phase_ids
        cls.launch.affectation_ids.affected = True
        return cls.phase.affectation_ids | cls.launchs.affectation_ids
    
    @classmethod
    def _spread_affect(cls):
        """ Affect:
            - position1 to phase1 & launch1
            - position2 to ...
        """
        for i, phase in enumerate(cls.phases):
            phase.lot_ids = cls.lots[i]
            affectation = phase.affectation_ids
            affectation.quantity_affected = affectation.quantity_remaining_to_affect
        
        for i, launch in enumerate(cls.launchs):
            launch.phase_ids = cls.phases[i]
            launch.affectation_ids.affected = True
        
        return cls.phase.affectation_ids | cls.launchs.affectation_ids
    
    @classmethod
    def _reset_affectations(cls, spread=False):
        """ Restart project's affectations
            Useful to restart tests from a clean basis without
             deleting all the project
        """
        cls.project.unlink()
        cls._create_project('Project1')

        if spread:
            cls._spread_affect()
        else:
            cls._quick_affect()

    @classmethod
    def _create_new_position(cls):
        """ Creates a new position with qty """
        cls.new_position = cls.position.copy()
    