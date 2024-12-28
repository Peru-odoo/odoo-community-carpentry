# -*- coding: utf-8 -*-

from odoo import exceptions, fields, Command
from odoo.tests import common, Form
import base64

from odoo.addons.base.tests.test_ir_attachment import TestIrAttachment

class TestCarpentryPurchase(TestIrAttachment):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Partner
        ResPartner = cls.env['res.partner']
        cls.partner = ResPartner.create({'name': 'Partner'})
        cls.delivery = ResPartner.create({
            'name': 'somewhere',
            'type': 'delivery',
            'parent_id': cls.partner.id
        })

        # Project
        cls.project = cls.env['project.project'].create({
            'name': 'Project Test 01'
        })

        cls.order = cls.env['purchase.order'].create({
            'partner_id': cls.partner.id,
            'project_id': cls.project.id,
            'description': 'Purchase Order Test 01'
        })
    

    def test_01_project_partner(self):
        with Form(self.project) as f:
            f.partner_id = self.partner
        self.assertEqual(self.project.delivery_address_id, self.delivery)
