# -*- coding: utf-8 -*-

from odoo import exceptions, fields, Command
from odoo.tests import Form

from odoo.addons.carpentry_purchase_budget.tests.test_carpentry_purchase_budget import TestCarpentryPurchaseBudget_Base

class TestCarpentryMrpBudget_Base(TestCarpentryPurchaseBudget_Base):

    DURATION_EXPECTED = 5.0 * 60 # 5 hours

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # workcenter
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Test Workcenter 001',
            'costs_hour_account_id': cls.analytic.id,
        })

        # product
        cls.consu, = cls.env['product.product'].create([{
            'name': 'Product Consu Test 001',
            'detailed_type': 'consu',
        }])

        # manufacturing order
        cls.mo = cls.env['mrp.production'].create([{
            'project_id': cls.project.id,
            'launch_ids': cls.project.launch_ids.ids,
            'product_id': cls.product.id,
            'workorder_ids': [Command.create({
                'name': 'WorkOrder Test 001',
                'workcenter_id': cls.workcenter.id,
                'duration_expected': cls.DURATION_EXPECTED
            })]
        }])
        cls.mo.move_raw_ids = [Command.create(
            cls.mo._get_move_raw_values(cls.consu, 1.0, cls.consu.uom_id) | {
                'production_id': False,
                'price_unit': cls.UNIT_PRICE,
            },
        )]


class TestCarpentryMrpBudget(TestCarpentryMrpBudget_Base):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
    
    # ---- Manufacturing Order ----
    def test_01_mo_analytic_choice(self):
        """ Test manual choice of analytics (+1 project's global budget) """
        with Form(self.mo) as f:
            f.budget_analytic_ids.add(self.analytic_global)
        self.assertTrue(self.mo.affectation_ids)
    
    def test_02_mo_affectation_full(self):
        """ Test if budget reservation matrix forms well
            - `record_ref: add all launches (row)
            - `group_ref`: 1 per-position analytic (col)
        """
        with Form(self.mo) as f:
            f.budget_analytic_ids.add(self.analytic)
        
        aff = self.mo.affectation_ids
        self.assertEqual(len(aff), len(self.project.launch_ids) + 1)

        # Test if mo expense is well distributed per launch for the automated budget reservation
        # Expected result: all expense on launch 1, since this only launch has available budget
        self.assertEqual(aff[0].quantity_affected, self.DURATION_EXPECTED / 60)
        self.assertEqual(aff[1].quantity_affected, 0)
        self.assertEqual(aff[2].quantity_affected, 0)
