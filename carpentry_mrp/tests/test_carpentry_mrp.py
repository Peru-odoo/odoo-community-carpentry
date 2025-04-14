# -*- coding: utf-8 -*-

from odoo import exceptions, fields, Command
from odoo.addons.carpentry_purchase.tests.test_carpentry_purchase import TestCarpentryPurchase_Base

class TestCarpentryMrp_Base(TestCarpentryPurchase_Base):

    PRODUCT_QTY_TODO = 10.0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # manufacturing order
        cls.mo = cls.env['mrp.production'].create([{
            'project_id': cls.project.id,
            'product_id': cls.product_stock.id
        }])
        cls.mo.move_raw_ids = [Command.create(
            cls.mo._get_move_raw_values(cls.product_consu, cls.PRODUCT_QTY_TODO, cls.consu.uom_id) | {
                'production_id': False
            },
        )]

class TestCarpentryMrp(TestCarpentryMrp_Base):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
    
    def test_01_is_done(self):
        """ Test overwrittance of `_compute_is_done` """
        self.assertFalse(self.move_raw_product4.is_done)
        self.move_raw_product4.quantity_done = self.PRODUCT_UOM_QTY
        self.assertTrue(self.move_raw_product4.is_done)
