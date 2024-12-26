# -*- coding: utf-8 -*-

from odoo import exceptions, fields, Command
from odoo.tests import common, Form

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.carpentry_position_budget.test.test_00_position_budget_base import TestCarpentryPositionBudget_Base

class TestCarpentryPurchaseBudget(AccountTestInvoicingCommon, TestCarpentryPositionBudget_Base):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.purchase = self.env['purchase.order'].create({
            'partner_id': cls.partner_a.id,
            'order_line': [Command.create({
                'product_id': cls.product_a.id,
                'product_qty': 1,
                'price_unit': 100,
            }), Command.create({
                'product_id': cls.product_b.id,
                'product_qty': 10,
                'price_unit': 200,
            })]
        })

    #----- shortcut -----
    def test_01_shortcut_analytic_project(self):
        """ Test if **project** analytic account is well set on line (in mass) """
        pass

    def test_02_shortcut_analytic_budget(self):
        """ Test if project analytic account is:
            - well computed (to line's if single)
            - well set to *empty* lines
        """
        pass

    #----- affectation matrix -----
    def test_03_launch_ids(self):
        """ Test if `launch_ids` O2m computed fields forms well from *real* affectations """

    def test_04_affectation_temp(self):
        """ Test if budget reservation matrix forms well:
            - `record_ref: add/remove launches (row), from `launch_ids` O2m computed
            - `group_ref`: add/remove analytics (col), from `analytic_distribution` of PO's lines
            - `section_ref`: PO id
        """
        pass
    
    #----- budget logics -----
    def test_05_auto_update_budget_distribution(self):
        """ Test auto-budget reservation button (expense -> budget) """
        pass
    
    def test_06_warning_budget(self):
        """ Test warning banner display (if totals of untaxed != budget reservation) """
        self.assertEqual(self.purchase.warning_budget, False)
        self.assertEqual(self.purchase.warning_budget, True)
        pass
        