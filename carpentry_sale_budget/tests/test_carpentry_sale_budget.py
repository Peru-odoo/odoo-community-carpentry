# -*- coding: utf-8 -*-

from odoo import exceptions, fields, Command
from odoo.tests import common, Form

from odoo.addons.carpentry_sale.tests.test_carpentry_sale import TestCarpentrySale

class TestCarpentrySaleBudget(TestCarpentrySale):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_margins_fees(self):
        """ To simplify, let's test the margins only with fees (not the budget) """
        self.project.fees_prorata_rate = 15 # %
        self.assertEqual(self.project.margin_contributive, round(self.project.market_reviewed * 0.85, 1))

    def test_02_budget_up_to_date(self):
        # Not fully updated yet
        sol1 = fields.first(self.order.order_line)
        sol1.budget_updated = True
        self.assertEqual(self.order.lines_budget_updated, 'not_updated')
        self.assertFalse(self.project.budget_up_to_date)

        # Fully updated
        self.order.order_line.budget_updated = True
        self.assertEqual(self.order.lines_budget_updated, 'all_updated')
        self.assertTrue(self.project.budget_up_to_date)
