# -*- coding: utf-8 -*-

import math

from odoo.addons.carpentry_position_budget.tests.test_05_analytic_project import (
    TestCarpentryPositionBudget_AnalyticBase,
    TestCarpentryPositionBudget_AnalyticProject,
    TestCarpentryPositionBudget_AnalyticEnforcement
)
from odoo.addons.carpentry_position_budget.tests.test_06_reservation import (
    TestCarpentryPositionBudget_Reservation,
)

class TestCarpentryPurchaseBudget_Base(TestCarpentryPositionBudget_AnalyticBase):
    record_model = 'purchase.order'
    field_lines = 'order_line'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

class TestCarpentryPurchaseBudget_AnalyticProject(
    TestCarpentryPositionBudget_AnalyticProject,
    TestCarpentryPurchaseBudget_Base,
):
    @classmethod
    def setUpClass(cls):
        super(TestCarpentryPurchaseBudget_AnalyticProject, cls).setUpClass()

        # PO without `project_id` to start with
        cls.po = cls.Model.create({
            'partner_id': cls.env.user.partner_id.id,
        })
        cls.po_line, _ = cls.Line.create([{
            'order_id': cls.po.id,
            'product_id': cls.product.id,
            'product_qty': 1.0,
            'price_unit': cls.UNIT_PRICE,
        }, {
            'order_id': cls.po.id,
            'product_id': cls.product_storable.id,
            'product_qty': 1.0,
            'price_unit': cls.UNIT_PRICE,
        }])
    
    def test_01_set_record_project_after_line_creation(self):
        """ On PO, project can be set *after* the PO and lines creation
            (replenishment from stock).
            
            => Test that, from a record with existing lines,
               setting the record's project cascades well to lines
        """
        # no projects analytics at first
        self._test_line_projects(self.env['project.project'], line=self.po_line)

        # set a project on PO after PO's creation: line's project should take it
        self.po.project_id = self.project
        self._test_line_projects(self.project, line=self.po_line)

    def test_02_remove_record_project(self):
        """ Ensure record's project removal is cascaded to lines """
        self.po.project_id = False
        self._test_line_projects(self.env['project.project'], line=self.po_line)

    def test_03_project_on_analytic_distrib_before_record(self):
        """ Test case where line analytic is set *before* record's `project_id`
            -> Changing record's project **MUST** cascade on line
        """
        # set line's analytic *before* the record's, with different projects
        self._add_analytic({self.project2_aac.id: 100}, self.po_line)
        self.po.project_id = self.project

        # the record's project should have cascaded
        self._test_line_projects(self.project, line=self.po_line)

class TestCarpentryPurchaseBudget_AnalyticEnforcement(
    TestCarpentryPositionBudget_AnalyticEnforcement,
    TestCarpentryPurchaseBudget_Base,
):
    @classmethod
    def setUpClass(cls):
        super(TestCarpentryPurchaseBudget_AnalyticEnforcement, cls).setUpClass()


class TestCarpentryPurchaseBudget_Reservation(
    TestCarpentryPositionBudget_Reservation,
    TestCarpentryPurchaseBudget_Base
):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    
    #===== Auto/suggestion mode =====#
    # See `carpentry_position_budget/TestCarpentryPositionBudget_Reservation`
    def _test_01_results(self):
        return {
            'count': 1,
            'aacs': self.aac_other,
            'launchs': self.env['carpentry.group.launch'],
            'other_expense_aacs': self.aac_installation, # `installation` should be in `other_expense_ids`
            'budget_reserved': self.UNIT_PRICE * 0.50,
            'budgetable': self.UNIT_PRICE,
            'expense_valued': self.UNIT_PRICE,
            'gain': -1 * self.UNIT_PRICE * 0.50, # expense > reserved budget
        }
    
    def _test_03_results(self):
        return {
            'count': 2,
            'aacs': self.aac_other + self.aac_installation,
            'launchs': self.launch,
            'other_expense_aacs': self.Analytic,
            'budget_reserved': self.UNIT_PRICE,
            'budgetable': self.UNIT_PRICE,
            'expense_valued': self.UNIT_PRICE,
            'gain': 0, # there's enough remaining budget: reservation should equal expense
        }
    
    #===== Manual mode =====#
    def _test_04_results(self, all_aacs):
        return {
            'count': 3,
            'aacs': all_aacs,
            'launchs': self.launch,
            'other_expense_aacs': self.Analytic,
            'gain': 0, # budget is available => gain still == 0
        }

    def test_04_manual_budget_add_available(self):
        """ Ensure when adding a new budget center manually,
            the po line's analytic distrib is modified,
            to split the expense between selected `budget_analytic_ids`
        """
        all_aacs = self.aac_other + self.aac_installation + self.aac_production
        prev_distrib = self.line.analytic_distribution

        super().test_04_manual_budget_add_available()
        
        new_distrib = self.line.analytic_distribution
        self.assertNotEqual(prev_distrib, new_distrib)
        self.assertTrue(all([
            str(aac_id) in new_distrib.keys()
            and math.floor(new_distrib[str(aac_id)]) == 33 # 3 budget centers => 33%
            for aac_id in all_aacs.ids
        ]))

    def _test_05_results(self):
        # expense is (manually) splitted over 3 analytic
        # with precision '2 digits'
        expense_ratio = self.line.price_unit * 33.33 / 100 * 3

        return {
            'other_expense_aacs': self.Analytic,
            'budget_reserved': self.project.budget_total,
            'budgetable': expense_ratio,
            'expense_valued': expense_ratio,
            'gain': self.project.budget_total - expense_ratio,
        }
    
    def _test_06_results(self):
        return super()._test_06_results() | {
            'gain': 0, # budget is available => gain still == 0
        }
    
    def _test_08_results(self):
        return super()._test_08_results() | {
            'budget_reserved': self.UNIT_PRICE,
            'budgetable': self.UNIT_PRICE * 2, # 2 aac on 50% and 1 on 100% in analytic_distrib (complex case)
            'expense_valued': self.UNIT_PRICE * 2,
            'gain': -1 * self.UNIT_PRICE,
        }
    
    #===== PO specific =====#
    def test_80_budgetable_amount(self):
        """ Ensure even in PO with storable product,
            budgetable amount is only sum of consumable
        """
        # po has 2 products: 1 consumable, 1 internal
        self.line.analytic_distribution = {self.aac_goods.id: 100} # ensure normal analytic of consu line
        self.assertEqual(self.record.total_budgetable, self.UNIT_PRICE)
        self.assertEqual(self.record.amount_untaxed, self.UNIT_PRICE * 2)

    def test_81_other_expense_bill(self):
        """ Ensure if the analytic is changed on account.move and
            is different to PO's lines, it takes precedence and
            goes to `other_expense_ids`
        """
        pass
        # TODO @arnaudlayec

    def test_82_can_chose_budgets_when_billed(self):
        """ Ensure even if some real expenses comes from the account.move.line,
            analytics of the bill does not interfer in recomputation of `budget_analytic_ids`
        """
        pass
        # TODO @arnaudlayec
        
        # if changed manually: does not interfer

        # if retriggered (e.g. change PO's analytic): included
