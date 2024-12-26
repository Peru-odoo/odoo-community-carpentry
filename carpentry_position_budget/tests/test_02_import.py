# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command
from odoo.tests import common, Form

from odoo.tools import file_open
import base64

from .test_00_position_budget_base import TestCarpentryPositionBudget_Base

class TestCarpentryPositionBudget_Import(TestCarpentryPositionBudget_Base):

    BUDGET_INSTALL = 10.0
    ORGADATA_FILENAME = 'REPORT_MEXT.zip'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # new clean project
        cls.project_import = cls.project.copy({'name': 'Test Project Import 01'})

        # import wizard
        cls._open_wizard(cls, cls.project_import)
    
    def _open_wizard(self, project_id, vals={}):
        file_res = file_open('carpentry_position_budget/tests/' + self.ORGADATA_FILENAME, 'rb')
        mdb_file = file_res.read()
        self.Wizard = self.env['carpentry.position.budget.import.wizard']
        self.wizard = self.Wizard.create([{
            'project_id': project_id.id,
            'external_db_type': 'orgadata',
            'import_file': base64.b64encode(mdb_file),
            'filename': self.ORGADATA_FILENAME
        } | vals])
        self.wizard.button_truncate_budget()
        file_res.close()


    def test_01_truncate_budget(self):
        self.position.position_budget_ids = [Command.create({
            'analytic_account_id': self.aac_install.id,
            'amount': self.BUDGET_INSTALL
        })]
        self.assertTrue(self.position.budget_install, self.BUDGET_INSTALL)
        self.wizard.button_truncate_budget()
        self.assertTrue(self.position.budget_install, 0.0)

    def test_02_import_file_orgadata(self):
        """ Test import logic and verify positions, lots and budgets were added """
        self.wizard.button_import()
        self.assertTrue(self.project_import.lot_ids.ids)
        self.assertTrue(self.project_import.position_ids.ids)
        self.assertTrue(self.project_import.position_budget_ids.ids)

    def test_03_project_totals(self):
        """ Test project totals computation """
        self.assertTrue(self.project_import.budget_line_ids.ids)
        
        # project totals
        self.assertTrue(self.project_import.budget_install)
        self.assertTrue(self.project_import.budget_prod)
        self.assertTrue(self.project_import.budget_global_cost)

    def test_04_budget_coef(self):
        """ Test coefficient: new import with 40% coef """
        prod_before = self.project_import.budget_prod
        self._open_wizard(self.project_import, {'budget_coef': 40})
        self.wizard.button_import()

        self.assertEqual(round(prod_before * 40/100, 2), round(self.project_import.budget_prod, 2))
    
    def test_05_column_mode_ignore(self):
        """ Test ignoring/only with some columns """
        # Ignore PROD: we should have budget but not of PROD
        self._open_wizard(self.project_import, {
            'column_mode': 'ignore',
            'column_ids': [Command.set(self.interface_fab2.ids)]
        })
        self.wizard.button_import()
        self.assertFalse(self.project_import.budget_prod)
        self.assertTrue(self.project_import.budget_install)

        # Only PROD: we should have PROD but no other
        self._open_wizard(self.project_import, {
            'column_mode': 'only',
            'column_ids': [Command.set(self.interface_fab2.ids)]
        })
        self.wizard.button_import()
        self.assertTrue(self.project_import.budget_prod)
        self.assertFalse(self.project_import.budget_install)
