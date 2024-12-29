# -*- coding: utf-8 -*-

from odoo import exceptions, fields, Command
from odoo.tests import common, Form
from odoo.tools import file_open

import base64

class TestCarpentryMrpImport(common.SingleTransactionCase):

    FILENAME = 'orgadata_test.sqlite3'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.project = cls.env['project.project'].create({'name': 'Project Test 001'})

        # Products
        cls.final_product, cls.storable, cls.replacement, cls.ignored, cls.consu = cls.env['product.product'].create([{
            'name': 'Position Final Product Test 001',
            'default_code': False,
        }, {
            'name': 'Vis TF cruciforme ø 4,8x30',
            'default_code': '205082',
            'type': 'product',
        }, {
            'name': 'Replacement',
            'default_code': '218156',
            'type': 'product',
        }, {
            'name': 'Ignored',
            'default_code': '236253',
            'type': 'product',
            'purchase_ok': False,
        }, {
            'name': 'Consummable',
            'default_code': '269510',
            'type': 'consu',
        }])
        cls.substituted = cls.replacement.copy({
            'name': 'Substituted',
            'default_code': '218157',
            'product_substitution_id': cls.replacement.id
        })

        # Manufacturing Order
        cls.mo = cls.env['mrp.production'].create([{
            'project_id': cls.project.id,
            'product_id': cls.final_product.id
        }])

        cls._load_wizard()
    
    @classmethod
    def _load_wizard(self):
        # Open Wizard & upload file
        file_res = file_open('carpentry_mrp_import/tests/' + self.FILENAME, 'rb')
        file_content = file_res.read()
        Wizard = self.env['carpentry.mrp.import.wizard']
        self.wizard = Wizard.create([{
            'production_id': self.mo.id,
            'external_db_type': 'orgadata',
            'import_file': base64.b64encode(file_content),
            'filename': self.FILENAME
        }])
        file_res.close()

    def test_01_load_file(self):
        # Load external database
        self.wizard.button_import()
        self.assertTrue(self.wizard.imported_product_ids)
    
    def test_02_filter(self):
        self.assertTrue(self.storable in self.wizard.imported_product_ids)
        self.assertTrue(self.replacement in self.wizard.imported_product_ids)
        self.assertEqual(self.substituted, self.wizard.substituted_product_ids)
        self.assertEqual(self.ignored, self.wizard.ignored_product_ids)
        self.assertEqual(self.consu, self.wizard.non_stored_product_ids)

    def test_03_unknown_xlsx(self):
        self.assertTrue(self.wizard.unknown_product_xlsx)
    
    def test_04_import_component(self):
        self.assertTrue(self.storable in self.mo.move_raw_ids.product_id)
    