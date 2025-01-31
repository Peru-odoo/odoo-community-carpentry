# -*- coding: utf-8 -*-

from odoo import exceptions, fields, Command
from odoo.tests import Form

from odoo.addons.carpentry_position.tests.test_carpentry_position import TestCarpentryPosition_Base

class TestCarpentryPurchaseBudget_Base(TestCarpentryPosition_Base):

    BUDGET_POSITION = 10.0
    UNIT_PRICE = 150.0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # project & carpentry
        cls.project.write({
            'date_start': '2022-01-01',
            'date': '2022-12-31',
        })
        
        # affect all positions to phase1 and launch1 (qty=0 but position1-phase1)
        cls._clean_affectations(quick_affect=True)
        cls.phase.affectation_ids[0].quantity_affected = 1

        # analytic
        cls.plan = cls.env.company.analytic_budget_plan_id
        cls.analytic = cls.env['account.analytic.account'].create({
            'name': 'Account Test 01',
            'plan_id': cls.plan.id,
            'budget_type': 'goods',
        })
        cls.analytic2 = cls.analytic.copy({'name': 'Account Test 02'})

        # budget lines template
        cls.budget = fields.first(cls.project.budget_ids)
        cls.account = cls.env["account.account"].create({
            "code": "accounttest01",
            "name": "Test Account 01",
            "account_type": "asset_fixed",
        })
        cls.env['account.move.budget.line.template'].create([{
            'analytic_account_id': cls.analytic.id,
            'account_id': cls.account.id,
        }, {
            'analytic_account_id': cls.analytic2.id,
            'account_id': cls.account.id,
        }])

        # position budget
        cls.position.position_budget_ids = [
            Command.create({
                'analytic_account_id': cls.analytic2.id,
                'amount': cls.BUDGET_POSITION
            }), Command.create({
                'analytic_account_id': cls.analytic.id,
                'amount': cls.BUDGET_POSITION
            })
        ]

        # product
        cls.product = cls.env['product.product'].create({
            'name': 'Product Test 01',
            'detailed_type': 'consu',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
        })
        
        # purchase order
        cls.purchase = cls.env['purchase.order'].create({
            'partner_id': cls.env.user.partner_id.id,
            'order_line': [Command.create({
                'product_id': cls.product.id,
                'product_qty': 1,
                'price_unit': cls.UNIT_PRICE,
            }), Command.create({
                'product_id': cls.product.id,
                'product_qty': 1,
                'price_unit': cls.UNIT_PRICE,
            })]
        })
        cls.line = fields.first(cls.purchase.order_line)

        # global budget
        cls.analytic_global = cls.analytic.copy({'name': 'Account Global Test 03'})
        cls.project.budget_line_ids = [Command.create({
            'budget_id': cls.project.budget_id.id,
            'analytic_account_id': cls.analytic_global.id,
            'account_id': cls.account.id,
            'date': cls.project.date_start,
        })]


class TestCarpentryPurchaseBudget(TestCarpentryPurchaseBudget_Base):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
    

    def _set_full_affectation(self):
        po = self.purchase
        po.project_id = self.project.id
        po.launch_ids = [Command.set(self.project.launch_ids.ids)]
        po.order_line.analytic_distribution = {self.analytic.id: 50}
    
    def test_01_affectation_full(self):
        """ Test if budget reservation matrix forms well
            - `record_ref: add all launches (row)
            - `group_ref`: add all analytics (col)
        """
        self._set_full_affectation()
        aff = self.purchase.affectation_ids
        self.assertEqual(len(aff), len(self.project.launch_ids))

        # Test if purchase expense is well distributed per launch for the automated budget reservation
        # Expected result: all expense on launch 1, since this only launch has available budget
        self.assertEqual(aff[0].quantity_affected, self.BUDGET_POSITION)
        self.assertEqual(aff[1].quantity_affected, 0)
        self.assertEqual(aff[2].quantity_affected, 0)

    def test_02_affectation_empty_budget(self):
        """ Test if budget matrix empty itself if no budget """
        self._set_full_affectation()
        for line in self.purchase.order_line:
            with Form(line) as f:
                f.analytic_distribution = {}
        self.assertFalse(self.purchase.affectation_ids)

    def test_03_affectation_single_launch(self):
        """ Test if budget matrix & content well comes back to 1 launch (from all launches) """
        self._set_full_affectation() # starts with a complete matrix
        self.purchase.launch_ids = [Command.set(self.launch.ids)] # remove 2 launches
        self.assertEqual(len(self.purchase.affectation_ids), 1) # ensure we only have 3-2=1 launch in the budget matrix

        # Also ensure all the budget reservation is automatically set on the launch
        self.assertEqual(
            self.purchase.affectation_ids.quantity_affected,
            self.BUDGET_POSITION
        )
    
    def test_04_analytic_choice(self):
        """ Test manual choice of analytics """
        with Form(self.purchase) as f:
            f.budget_analytic_ids.remove(id=self.analytic.id)
            f.budget_analytic_ids.add(self.analytic2)
        
        lines = self.purchase.order_line.filtered(lambda x: x.product_id.type != 'product')
        self.assertEqual(self.analytic2, lines.analytic_ids.filtered('is_project_budget'))
    
    def test_05_global_cost(self):
        """ Test if global costs is well set on project and not on any launches """
        self._set_full_affectation() # on 3 launches
        with Form(self.purchase) as f:
            # 1 single global (& manual) budget
            f.budget_analytic_ids.remove(id=self.analytic.id)
            f.budget_analytic_ids.add(self.analytic_global)
        
        # manual+global budget: well set on lines?
        lines = self.purchase.order_line.filtered(lambda x: x.product_id.type != 'product')
        self.assertEqual(self.analytic_global, lines.analytic_ids.filtered('is_project_budget'))
        # affectation matrix: only 1 row, linked to project instead of launch ?
        self.assertEqual(len(self.purchase.affectation_ids), 1)
        self.assertEqual(self.purchase.affectation_ids.record_ref, self.project)
        self.assertEqual(self.purchase.affectation_ids.group_ref, self.analytic_global)
