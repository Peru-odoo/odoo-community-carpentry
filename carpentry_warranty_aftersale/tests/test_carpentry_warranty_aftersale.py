# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command
from odoo.tests import common

class TestCarpentryWarrantyAftersale(common.SingleTransactionCase):

    # @classmethod
    # def setUpClass(cls):
    #     super().setUpClass()

    #     cls.project = cls._create_project_with_test_data(cls, 'Project Test 1')
        
    #     cls.Affectation = cls.env['carpentry.group.affectation']
    #     cls.AffectationTemp = cls.env['carpentry.group.affectation.temp']
    
    # def _create_project_with_test_data(self, project_name):
    #     Project = self.env['project.project']
    #     project = Project.create({'name': project_name})

    #     # Create 3 lots, phases, launches
    #     group_vals_list = [
    #         {'project_id': project.id, 'name': f'{project.name} - Group Test {i}'}
    #         for i in [1,2,3]
    #     ]
    #     lot_ids = self.env['carpentry.group.lot'].create(group_vals_list)
    #     phase_ids = self.env['carpentry.group.phase'].create(group_vals_list)
    #     launch_ids = self.env['carpentry.group.launch'].create(group_vals_list)

    #     # Create 3 positions, 1 per lot
    #     position_ids = self.env['carpentry.position'].create([
    #         {
    #             'project_id': project.id,
    #             'name': 'Position' + str(i),
    #             'quantity': i+1,
    #             'lot_id': lot.id
    #         }
    #         for i, lot in enumerate(project.lot_ids)
    #     ])

    #     return project
