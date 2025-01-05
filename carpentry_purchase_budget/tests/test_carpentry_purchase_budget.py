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
        cls.project2 = cls.project.copy({'name': 'Project Test 002'})
        
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

        # budget lines tempalte
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



class TestCarpentryPurchaseBudget(TestCarpentryPurchaseBudget_Base):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
    
    #----- analytic shortcuts & constrains of purchase order lines -----
    def test_01_shortcut_analytic_project(self):
        """ Test if **project** analytic account is well set on line (in mass) """
        # Set project2 first, and ensure the new 'self.project' wins over the former one
        with Form(self.purchase) as f:
            f.project_id = self.project2
        with Form(self.purchase) as f:
            f.project_id = self.project
        
        self.assertTrue(all(
            self.project.analytic_account_id in line.analytic_ids and
            not self.project2.analytic_account_id in line.analytic_ids
            for line in self.purchase.order_line
        ))

    def test_02_raise_analytic_project(self):
        """ Should raise: cannot set different project analytic than the one in `project_id` """
        self.purchase.project_id = self.project
        with self.assertRaises(exceptions.ValidationError):
            self.line.analytic_distribution = {self.project2.analytic_account_id.id: 100}

    def test_03_shortcut_analytic_budget(self):
        """ Test if analytic account well applies to PO's lines (in mass) """
        # Set `self.analytic2` first, and ensure the new 'self.analytic' wins over the former one
        with Form(self.purchase) as f:
            f.budget_unique_analytic_id = self.analytic2
        with Form(self.purchase) as f:
            f.budget_unique_analytic_id = self.analytic
        
        self.assertTrue(all(
            self.analytic == line.analytic_ids.filtered('is_project_budget')
            for line in self.purchase.order_line
        ))

    # def test_04_raise_analytic_budget(self):
    #     """ Should raise: cannot set budget analytic on PO lines
    #         of an analytic account not in project's budget lines
    #     """
    #     self.purchase.project_id = self.project

    #     # Remove budget on `analytic2`
    #     fields.first(self.position.position_budget_ids).unlink()

    #     # `analytic2` is not in the budget of `self.project` => should raise
    #     with self.assertRaises(exceptions.ValidationError):
    #         self.line.analytic_distribution = {self.analytic2.id: 100}

    #----- affectation matrix -----
    def _set_full_affectation(self):
        po = self.purchase
        po.project_id = self.project.id
        po.launch_ids = [Command.set(self.project.launch_ids.ids)]
        po.order_line.analytic_distribution = {self.analytic.id: 50}
    
    def test_05_affectation_full(self):
        """ Test if budget reservation matrix forms well
            - `record_ref: add all launches (row)
            - `group_ref`: add all analytics (col)
        """
        self._set_full_affectation()
        self.assertEqual(len(self.purchase.affectation_ids), len(self.project.launch_ids))

        # Test if purchase expense is well distributed per launch for the automated budget reservation
        # Expected result: all expense on launch 1, since this only launch has available budget
        a = self.purchase.affectation_ids
        self.assertEqual(a[0].quantity_affected, self.BUDGET_POSITION)
        self.assertEqual(a[1].quantity_affected, 0)
        self.assertEqual(a[2].quantity_affected, 0)

    def test_06_affectation_empty_budget(self):
        """ Test if budget matrix empty itself if no budget """
        self._set_full_affectation()
        for line in self.purchase.order_line:
            with Form(line) as f:
                f.analytic_distribution = {}
        self.assertFalse(self.purchase.affectation_ids)

    def test_07_affectation_single_launch(self):
        """ Test if budget matrix & content well comes back to 1 launch (from all launches) """
        self._set_full_affectation() # starts with a complete matrix
        self.purchase.launch_ids = [Command.set(self.launch.ids)] # remove 2 launches
        self.assertEqual(len(self.purchase.affectation_ids), 1) # ensure we only have 3-2=1 launch in the budget matrix

        # Also ensure all the budget reservation is automatically set on the launch
        self.assertEqual(
            self.purchase.affectation_ids.quantity_affected,
            self.BUDGET_POSITION
        )
    