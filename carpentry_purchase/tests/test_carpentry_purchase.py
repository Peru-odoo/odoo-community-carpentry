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
        self.assertTrue(self.order.warning_stock)
    
    #===== purchase.order.line (project analytic affectation) =====#
    # def test_03_shortcut_analytic_project(self):
    #     """ Test if **project** analytic account is well set on line (in mass) """
    #     # Set project2 first, and ensure the new 'self.project' wins over the former one
    #     with Form(self.order) as f:
    #         f.project_id = self.project2
    #     with Form(self.order) as f:
    #         f.project_id = self.project
    
    #     self.assertTrue(all(
    #         self.project.analytic_account_id in line.analytic_ids and
    #         not self.project2.analytic_account_id in line.analytic_ids
    #         for line in self.order.order_line
    #     ))

    def test_04_raise_analytic_project(self):
        """ Should raise: cannot set different project analytic than the one in `project_id` """
        self.order.project_id = self.project
        with self.assertRaises(exceptions.ValidationError):
            self.order.order_line.analytic_distribution = {self.project2.analytic_account_id.id: 100}

    def test_05_line_project_analytic_stock(self):
        aac_project = self.project.analytic_account_id
        aac_internal = self.env.company.internal_project_id.analytic_account_id

        # -- HERE 28/01/2025 --
        self.order.order_line._compute_analytic_ids() # necessary forced refresh
        self.assertTrue(aac_project not in self.line_stock.analytic_ids)
        self.assertTrue(aac_internal in self.line_stock.analytic_ids)
        self.assertTrue(aac_project in self.line_consu.analytic_ids)
        self.assertTrue(aac_internal not in self.line_consu.analytic_ids)

    #===== stock.picking =====#
    def test_06_picking_project(self):
        self.order.button_confirm()
        self.assertEqual(self.project, self.order.picking_ids.project_id)
    