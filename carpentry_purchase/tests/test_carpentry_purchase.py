# -*- coding: utf-8 -*-

from odoo import exceptions, fields, Command
from odoo.tests import common, tagged, Form

@tagged('post_install', '-at_install')
class TestCarpentryPurchase_Base(common.SingleTransactionCase):

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
        cls.project2 = cls.project.copy({'name': 'Project Test 002'})

        # Internal project (for PO line of stored product)
        internal = cls.env['project.project'].create({'name': 'Project Internal Test 01'})
        cls.env.company.internal_project_id = internal

        # Products
        uom_id = cls.env.ref('uom.product_uom_unit').id
        cls.product_stock = cls.env['product.product'].create({
            'name': 'Product Test 01',
            'detailed_type': 'product',
            'uom_id': uom_id,
            'uom_po_id': uom_id
        })
        cls.product_consu = cls.env['product.product'].create({
            'name': 'Product Test 02',
            'detailed_type': 'consu',
            'uom_id': uom_id,
            'uom_po_id': uom_id
        })

        # Purchase Order
        vals = {
            'product_uom': uom_id,
            'product_qty': 1.0,
            'price_unit': 1.0,
            'date_planned': fields.Date.today(),
        }
        cls.order = cls.env['purchase.order'].create({
            'partner_id': cls.env.user.partner_id.id,
            'project_id': cls.project.id,
            'description': 'Purchase Order Test 01',
            'order_line': [Command.create(vals | {
                'name': 'Test Line 01',
                'product_id': cls.product_stock.id,
            }), Command.create(vals | {
                'name': 'Test Line 02',
                'product_id': cls.product_consu.id,
            })]
        })
        cls.line_stock, cls.line_consu = cls.order.order_line
    


class TestCarpentryPurchase(TestCarpentryPurchase_Base):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
    
    #===== project.project =====#
    # def test_01_project_partner(self):
    #     with Form(self.project) as f:
    #         f.partner_id = self.partner
    #     self.assertEqual(self.project.delivery_address_id, self.delivery)

    #===== purchase.order =====#
    def test_02_warning_mix_stock(self):
        self.assertEqual(self.order.products_type, 'mix')

    #===== stock.picking =====#
    def test_03_picking_project(self):
        self.order.button_confirm()
        self.assertEqual(self.project, self.order.picking_ids.project_id)
    