# -*- coding: utf-8 -*-

from odoo import fields

from odoo.addons.carpentry_position_budget.tests.test_05_analytic_project import (
    TestCarpentryPositionBudget_AnalyticBase,
    TestCarpentryPositionBudget_AnalyticProject,
)
from .test_carpentry_01_picking_budget import TestCarpentryPickingBudget_Reservation

class TestCarpentryMrpBudget_Base(TestCarpentryPositionBudget_AnalyticBase):
    record_model = 'mrp.production'
    field_lines = 'move_raw_ids'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def _get_vals_record(cls):
        vals = super()._get_vals_record()
        vals.pop('partner_id')
        return vals | {'product_id': cls.product_storable.id}
    
    @classmethod
    def _get_vals_new_line(cls, product=None, qty=1.0, record=None):
        record = record or cls.record
        return record._get_move_raw_values(
            product_id=cls.product,
            product_uom_qty=1.0,
            product_uom=cls.product.uom_id
        ) | {
            'production_id': False,
            'price_unit': cls.UNIT_PRICE,
        }


class TestCarpentryMrpBudget_AnalyticProject(
    TestCarpentryPositionBudget_AnalyticProject,
    TestCarpentryMrpBudget_Base,
):
    @classmethod
    def setUpClass(cls):
        super(TestCarpentryMrpBudget_AnalyticProject, cls).setUpClass()



# (!!!) Tests of MRP are inherited from picking
class TestCarpentryMrpBudget_Reservation(
    TestCarpentryMrpBudget_Base,
    TestCarpentryPickingBudget_Reservation,
):
    @classmethod
    def setUpClass(cls):
        super(TestCarpentryMrpBudget_Reservation, cls).setUpClass()

        cls.expense = cls.UNIT_PRICE # of components only
    
    #===== Helper methods =====#
    @classmethod
    def _create_record_product(cls):
        super()._create_record_product()

    #===== Normalized tests =====#
    def _test_01_results(self):
        """ In MO:
            - `installation` goes to other expenses
            - `total_xxx` fields are splitted between components and workorders
        """
        return super()._test_01_results() | {
            'expense_aacs': self.aac_other + self.aac_installation,
            'other_expense_aacs': self.aac_installation,
            'gain': self.amount_other - self.expense, # -50.0 (only components)
        }
    
    def _test_03_results(self):
        """ Adding the 'installation' budget to the MO (from launch1)
            does not changes anything for components: same as 01
        """
        res = super()._test_03_results()
        self._set_reserved(min(
            self.amount_other,
            self.expense,
        ))
        return res | {
            'budget_reserved': self.reserved,
            'gain': self.reserved - self.expense, # still -50.0 (only components)
        }
    
    def _test_05_results(self):
        expense = self.product.standard_price # not * 2
        return super()._test_05_results() | {
            'budgetable': expense,
            'expense_valued': expense,
            'gain': self.reserved - expense,
        }
    
    def _test_08_results(self):
        expense = self.UNIT_PRICE * 2
        return super()._test_08_results() | {
            'budget_reserved': self.reserved,
            'budgetable': expense,
            'expense_valued': expense,
            'gain': self.reserved - expense,
        }
    
    #===== MO specific ======#
    @classmethod
    def _set_record_done(cls):
        cls.record.action_confirm()
        cls.record[cls.field_lines].quantity_done = 1.0
        cls.record.write({
            'qty_producing': 1.0,
            'product_qty': 1.0,
        })
        cls.record[cls.field_lines]._action_done()
        cls.record.button_mark_done()

    def test_80_workorder_budget_manual_add(self):
        """ Ensure when adding a new budget center of workorder,
            previous and new one are all kept,
            and that reservations lines & expense distribution are recomputed
        """
        # initial state: production is not in the MO
        self.assertFalse(self.aac_production in self.record.budget_analytic_ids)

        # add production in budget_analytic_ids_workorders
        # => it should stay
        self.record.budget_analytic_ids_workorders |= self.aac_production
        self.assertTrue(self.aac_production in self.record.budget_analytic_ids)

        # remove it production => it should leave
        self.record.budget_analytic_ids_workorders -= self.aac_production
        self.assertFalse(self.aac_production in self.record.budget_analytic_ids)

    def test_81_workorder_budget_dont_update_component(self):
        """ When choosing workorder budget, do not change anything to
            component's reservation or amounts
        """
        # initial state: there are components reservation, let's write `amount_reserved`
        prev_reservations = self._get_component_reservations()
        self.assertTrue(prev_reservations)
        prev_reservations.amount_reserved = 0.0

        # touch workorders budget center => should not change anything
        self.record.budget_analytic_ids_workorders |= self.aac_production
        self.env.invalidate_all()
        reservations = self._get_component_reservations()
        # same components reservations, no populate neither auto_reservation
        self.assertEqual(reservations, prev_reservations)
        self.assertTrue(all(x == 0.0 for x in reservations.mapped('amount_reserved')))
    
    def _get_component_reservations(self):
        return self.record.reservation_ids.filtered(
            lambda x: x.analytic_account_id in (
                self.record.budget_analytic_ids
                - self.record.budget_analytic_ids_workorders
            )
        )

    def test_82_workorder_budget_not_erased_by_component(self):
        """ When recomputing components (new raw, budget choice, ...)
            don't update workorder reservation table or amounts
        """
        # start situation: some workorder budget centers & `amount_reserved`
        reservations = self.record.reservation_ids - self._get_component_reservations()
        self.assertTrue(self.aac_production in self.record.budget_analytic_ids_workorders)
        reservations.amount_reserved = 1.0

        # button_force_refresh (components only)
        self.record.button_force_refresh()
        self.assertEqual(set(reservations.mapped('amount_reserved')), {1.0})

        # components's choice of budget centers
        self.record.budget_analytic_ids -= self.aac_other
        self.assertTrue(len(reservations))
        self.assertEqual(set(reservations.mapped('amount_reserved')), {1.0})

        # new raw material
        self.record.move_raw_ids |= fields.first(self.record.move_raw_ids).copy()
        self.assertTrue(len(reservations))
        self.assertEqual(set(reservations.mapped('amount_reserved')), {1.0})

    def test_83_difference_workorder_duration_budget(self):
        # start situation
        reservations = self.record.reservation_ids - self._get_component_reservations()
        self.assertTrue(bool(reservations))
        reservations.amount_reserved = 1.0

        # just test the compute
        self.assertEqual(
            self.record.difference_workorder_duration_budget,
            self.record.production_duration_expected / 60
            - sum(reservations.mapped('amount_reserved'))
        )
