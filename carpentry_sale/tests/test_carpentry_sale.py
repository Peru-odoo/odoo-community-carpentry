# -*- coding: utf-8 -*-

from odoo import exceptions, fields, Command
from odoo.tests import common, Form

class TestCarpentrySale(common.SingleTransactionCase):

    PRODUCT_PRICE = 10.0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Lead
        cls.lead = cls.env['crm.lead'].create({
            'name': 'Lead',
            'expected_revenue': 1234,
        })
        # Create project from opportunity
        cls.lead.action_create_project()
        cls.project = cls.lead.project_id

        # Partner
        ResPartner = cls.env['res.partner']
        cls.partner = ResPartner.create({'name': 'Partner'})

        # Product
        Product = cls.env['product.product']
        cls.product = Product.create({
            'name': 'Product',
            'list_price': cls.PRODUCT_PRICE,
        })

        # Sale Order
        cls.SaleOrder = cls.env['sale.order']
        cls.order = cls.SaleOrder.create({
            'description': 'Sale Order',
            'project_id': cls.project.id,
            'partner_id': cls.partner.id,
            'order_line': [
                Command.create({'product_id': cls.product.id}),
                Command.create({'product_id': cls.product.id}),
            ]
        })


    def test_01_convert_opportunity_to_project(self):
        """ Test if project's `Market` prefills well from opportunity's expected revenue """
        # Verify `Market` of project created from opportunity
        self.assertEqual(self.project.market, self.lead.expected_revenue)

        # Create project and then assign opportunity (test `onchange()`)
        project2 = self.project.copy({'name': 'Project'})
        lead2 = self.lead.copy()
        with Form(project2) as f2: # we need `Form()` to trigger `@api.onchange`
            f2.opportunity_id = lead2
        self.assertEqual(project2.market, lead2.expected_revenue)


    def test_02_sale_order_total_validated(self):
        """ Test if sale order's validated and unvalidated totals are calculated well,
            according to line's `validated` field
        """
        # validate 1 line =>  => standard total = 20.0 ; total validated = 10.0
        sol1 = fields.first(self.order.order_line)
        sol1.validated = True
        self.assertEqual(self.order.lines_validated, 'partial_validated')
        # total not depending "validated" line boolean
        self.assertEqual(self.order.amount_untaxed, self.PRODUCT_PRICE*2)
        self.assertEqual(self.project.sale_order_sum, self.PRODUCT_PRICE*2)
        # total **depending** "validated" line boolean
        self.assertEqual(self.order.amount_untaxed_validated, self.PRODUCT_PRICE)
        self.assertEqual(self.project.sale_order_sum_validated, self.PRODUCT_PRICE)
        self.assertFalse(self.project.sale_order_lines_fully_validated)

        # confirm the quotation => validate lines in mass => both total are equals
        self.order.action_confirm()
        self.assertEqual(self.order.amount_untaxed_validated, self.order.amount_untaxed)
        self.assertTrue(self.project.sale_order_lines_fully_validated)

        # test the search
        search_result = self.SaleOrder.search([('lines_validated', '=', 'all_validated')])
        self.assertEqual(self.order, search_result)

    def test_03_project_market_reviewed(self):
        self.assertEqual(self.project.sale_order_sum_validated, self.order.amount_untaxed_validated)
        self.assertEqual(self.project.market_reviewed, self.project.market + self.project.sale_order_sum_validated)
