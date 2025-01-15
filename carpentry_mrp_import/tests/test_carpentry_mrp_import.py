# -*- coding: utf-8 -*-

from odoo import exceptions, fields, Command
from odoo.tests import common, Form
from odoo.tools import file_open

import base64

class TestCarpentryMrpImport(common.SingleTransactionCase):

    COMPONENT_DB_FILE = 'orgadata_test.sqlite3'
    BYPRODUCTS_XLSX_FILE = 'byproducts_import_test.xlsx'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.project = cls.env['project.project'].create({'name': 'Project Test 001'})

        # Products
        Product = cls.env['product.product']
        cls.final_product, cls.storable, cls.replacement, cls.ignored, cls.consu = Product.create([{
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
            'active': False,
        }, {
            'name': 'Consummable',
            'default_code': '269510',
            'type': 'consu',
        }])
        cls.substituted = Product.create({
            'name': 'Substituted',
            'default_code': '218157',
            'type': 'product',
            'product_substitution_id': cls.replacement.id
        })

        # Manufacturing Order
        cls.mo = cls.env['mrp.production'].create([{
            'project_id': cls.project.id,
            'product_id': cls.final_product.id
        }])

        cls.wizard = cls._load_wizard()
    
    @classmethod
    def _load_wizard(self, mode='component'):
        # Open Wizard & upload file
        file = self.COMPONENT_DB_FILE if mode == 'component' else self.BYPRODUCTS_XLSX_FILE
        file_res = file_open('carpentry_mrp_import/tests/' + file, 'rb')
        file_content = file_res.read()

        Wizard = self.env['carpentry.mrp.import.wizard']
        wizard = Wizard.create([{
            'mode': mode,
            'production_id': self.mo.id,
            'external_db_type': 'orgadata',
            'import_file': base64.b64encode(file_content),
            'filename': self.COMPONENT_DB_FILE
        }])
        file_res.close()

        return wizard

    def test_01_load_file(self):
        # Load external database
        self.wizard.button_import()
        self.assertTrue(self.wizard.product_ids)
    
    def test_02_filter(self):
        self.assertTrue(self.storable in self.wizard.product_ids)
        self.assertTrue(self.replacement in self.wizard.product_ids)
        self.assertEqual(self.substituted, self.wizard.substituted_product_ids)
        self.assertEqual(self.ignored, self.wizard.with_context(active_test=False).ignored_product_ids)

    def test_03_import_component(self):
        self.assertTrue(self.wizard.supplierinfo_ids)
        self.assertTrue(self.storable in self.mo.move_raw_ids.product_id)
    
    def test_04_report_chatter(self):
        self.assertTrue(self.mo.message_ids)
        self.assertEqual(self.mo.message_attachment_count, 1)

    def test_05_byproducts_import(self):
        wizard = self._load_wizard('byproduct')
        wizard.button_import()
        self.assertTrue(self.mo.move_byproduct_ids)
