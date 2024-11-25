# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command
from odoo.tests import common, Form

from odoo.tools import file_open
import base64

from .test_00_position_budget_base import TestCarpentryPositionBudget_Base

class TestCarpentryPositionBudget_Import(TestCarpentryPositionBudget_Base):

    BUDGET_INSTALL = 10.0
    ORGADATA_FILENAME = 'vannes_ca_verrieres.zip'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # new clean project
        cls.project_import = cls.project.copy({'name': 'Test Project Import 01'})

        # import wizard
        file_res = file_open('carpentry_position_budget/tests/' + cls.ORGADATA_FILENAME, 'rb')
        mdb_file = file_res.read()
        cls.Wizard = cls.env['carpentry.position.budget.import.wizard']
        cls.wizard = cls.Wizard.create([{
            'project_id': cls.project_import.id,
            'external_db_type': 'orgadata',
            'import_file': base64.b64encode(mdb_file),
            'filename': cls.ORGADATA_FILENAME
        }])
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
        self.wizard.button_import()
        self.assertTrue(self.project_import.lot_ids.ids)
        self.assertTrue(self.project_import.position_ids.ids)
        self.assertTrue(self.project_import.position_budget_ids.ids)
        # project totals
        self.assertTrue(self.project_import.budget_install)
        self.assertTrue(self.project_import.budget_prod)
        self.assertTrue(self.project_import.budget_goods)
