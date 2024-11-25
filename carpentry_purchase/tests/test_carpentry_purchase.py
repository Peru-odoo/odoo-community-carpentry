# -*- coding: utf-8 -*-

from odoo import exceptions, fields, Command
from odoo.tests import common, Form

class TestCarpentrySale(common.SingleTransactionCase):

    PRODUCT_PRICE = 10.0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Partner
        ResPartner = cls.env['res.partner']
        cls.partner = ResPartner.create({'name': 'Partner'})

        # partner's Delivery address
        cls.delivery = ResPartner.create({
            'name': 'somewhere',
            'type': 'delivery',
            'parent_id': cls.partner.id
        })

        # Create project from opportunity
        cls.project = cls.env['project.project'].create({
            'name': 'Project Test 01'
        })

    def test_01_project_partner(self):
        with Form(self.project) as f:
            f.partner_id = self.partner
        self.assertEqual(self.project.partner_delivery_id, self.delivery)
        self.assertEqual(self.project.partner_invoice_id, self.partner)
