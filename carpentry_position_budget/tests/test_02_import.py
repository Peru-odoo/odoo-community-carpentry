# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command
from odoo.tests import common, Form

from odoo.tools import file_open
import base64

from .test_00_position_budget_base import TestCarpentryPositionBudget_Base

class TestCarpentryPositionBudget_Import(TestCarpentryPositionBudget_Base):

    budget_installation = 10.0
    ORGADATA_FILENAME = 'REPORT_MEXT.zip'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # import wizard
        cls._open_wizard(cls.project)
    
    @classmethod
    def _open_wizard(cls, project, vals={}):
        file_res = file_open('carpentry_position_budget/tests/' + cls.ORGADATA_FILENAME, 'rb')
        mdb_file = file_res.read()
        cls.Wizard = cls.env['carpentry.position.budget.import.wizard']
        cls.wizard = cls.Wizard.create([{
            'project_id': project.id,
            'external_db_type': 'orgadata',
            'import_file': base64.b64encode(mdb_file),
            'filename': cls.ORGADATA_FILENAME
        } | vals])
        cls.wizard.button_truncate_budget()
        file_res.close()


    def test_01_truncate_budget(self):
        self.position.position_budget_ids = [Command.create({
            'analytic_account_id': self.aac_installation.id,
            'amount_unitary': self.budget_installation
        })]
        self.assertEqual(self.position.budget_installation, self.budget_installation)
        self.wizard.button_truncate_budget()
        self.assertEqual(self.position.budget_installation, 0.0)

        self.project.position_ids.unlink()
        self.assertFalse(self.project.lot_ids)

    def test_02_import_file_orgadata(self):
        """ Test import logic and verify positions, lots and budgets were added """
        self.wizard.button_import()
        self.assertTrue(self.project.lot_ids.ids)
        self.assertTrue(self.project.position_ids.ids)
        self.assertTrue(self.project.position_budget_ids.ids)
        self.assertTrue(self.project.budget_line_ids.ids)
        self.assertTrue(self.project.budget_total)

    def test_03_budget_coef(self):
        """ Test coefficient: new import with 40% coef """
        prod_before = self.project.budget_production
        self._open_wizard(self.project, {'budget_coef': 40})
        self.wizard.button_import()

        self.assertEqual(
            round(prod_before * 40/100, 2),
            round(self.project.budget_production, 2)
        )
    
    def test_04_column_mode_ignore(self):
        """ Test ignoring/only with some columns """
        # Ignore PROD: we should have budget but not of PROD
        self._open_wizard(self.project, {
            'column_mode': 'ignore',
            'column_ids': [Command.set(self.interface_fab2.ids)]
        })
        self.wizard.button_import()
        self.assertFalse(self.project.budget_production)
        self.assertTrue(self.project.budget_installation)

        # Only PROD: we should have PROD but no other
        self._open_wizard(self.project, {
            'column_mode': 'only',
            'column_ids': [Command.set(self.interface_fab2.ids)]
        })
        self.wizard.button_import()
        self.assertTrue(self.project.budget_production)
        self.assertFalse(self.project.budget_installation)
