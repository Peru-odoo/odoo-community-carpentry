# -*- coding: utf-8 -*-

from odoo import Command

from odoo.addons.carpentry_position_budget.tests.test_05_analytic_project import (
    TestCarpentryPositionBudget_AnalyticBase,
    TestCarpentryPositionBudget_AnalyticProject,
)
from odoo.addons.carpentry_position_budget.tests.test_06_reservation import (
    TestCarpentryPositionBudget_Reservation,
)

class TestCarpentryPickingBudget_Base(TestCarpentryPositionBudget_AnalyticBase):
    record_model = 'stock.picking'
    field_lines = 'move_ids'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def _create_record_product(cls):
        cls.picking_type = cls.env.ref('stock.picking_type_out')
        cls.src_location = cls.picking_type.default_location_src_id

        super()._create_record_product()

    @classmethod
    def _get_vals_record(cls):
        return super()._get_vals_record() | {
            'picking_type_id': cls.picking_type.id,
        }
    
    @classmethod
    def _get_vals_new_line(cls, product=None, qty=1.0):
        """ switch keys `product_qty` -> `product_uom_qty` """
        vals = super()._get_vals_new_line()
        vals.pop('price_unit') # doesn't exist on `stock.move`
        return vals | {
            'name': cls.product.name,
            'product_uom_qty': vals.pop('product_qty'),
            'location_id': cls.src_location.id,
            'location_dest_id': cls.env.ref('stock.stock_location_locations_virtual').id,
        }

class TestCarpentryPickingBudget_AnalyticProject(
    TestCarpentryPositionBudget_AnalyticProject,
    TestCarpentryPickingBudget_Base,
):
    @classmethod
    def setUpClass(cls):
        super(TestCarpentryPickingBudget_AnalyticProject, cls).setUpClass()


class TestCarpentryPickingBudget_Reservation(
    TestCarpentryPositionBudget_Reservation,
    TestCarpentryPickingBudget_Base,
):
    @classmethod
    def setUpClass(cls):
        super(TestCarpentryPickingBudget_Reservation, cls).setUpClass()

        # picking total expense: 2 product lines of 150.0
        cls.expense = cls.UNIT_PRICE * 2
        cls._set_reserved(0.0)
    
    @classmethod
    def _set_reserved(cls, value):
        """ A pointer across tests """
        cls.reserved = value
    
    @classmethod
    def _print_debug(cls, modes=[]):
        if 'expense' in modes:
            expenses = cls.env['carpentry.budget.expense'].with_context(active_test=False)
            print('picking', cls.record.read(['expense_ids', 'other_expense_ids']))
            print('expenses', expenses.search_read(
                domain=[('picking_id', '=', cls.record.id)],
                fields=['analytic_account_id', 'amount_expense', 'amount_reserved'],
            ))

        if 'resa' in modes:
            print('reservations', cls.record.reservation_ids.read(['analytic_account_id', 'amount_reserved']))

        if 'default' in modes or not modes:
            print('picking', cls.record.read(['total_budget_reserved']))
            print('lines', cls.record.move_ids.read(['analytic_distribution', 'product_id', 'product_uom_qty', 'state']))
            print('products', cls.record.move_ids.product_id.read(['name', 'standard_price']))
    
    #===== Auto/suggestion mode =====#
    # See `carpentry_position_budget/TestCarpentryPositionBudget_Reservation`
    def _test_01_results(self):
        self._set_reserved(min(
            # result is 100.0: because not enough budget in 'amount_other'
            self.expense,
            self.amount_other,
        ))

        return {
            'count': 1,
            'aacs': self.aac_other,
            'launchs': self.env['carpentry.group.launch'],
            'expense_aacs': self.aac_other + self.aac_installation,
            'other_expense_aacs': self.aac_installation, # `installation` should be in `other_expense_ids`
            'budget_reserved': self.reserved,
            'budgetable': self.expense,
            'expense_valued': self.expense,
            'gain': self.amount_other - self.expense, # 100.0 - 300.0 = -200.0
        }
    
    def _test_03_results(self):
        """ There's still not enough budget on 'other' (100.0)
            but budget reservation grows thanks to 'installation',
             which has enough budget (150.0)
        """
        self._set_reserved(
            min(self.amount_other, self.expense) # 'other': same as 01
            + self.UNIT_PRICE # 'installation': enough budget
        )

        return {
            'count': 2,
            'aacs': self.aac_other + self.aac_installation,
            'launchs': self.launch,
            'other_expense_aacs': self.Analytic,
            'budget_reserved': self.reserved,
            'budgetable': self.expense,
            'expense_valued': self.expense,
            'gain': self.reserved - self.expense, # -50.0
        }
    
    #===== Manual mode =====#
    def _test_04_results(self, all_aacs):
        return {
            'count': 3,
            'aacs': all_aacs,
            'launchs': self.launch,
            'other_expense_aacs': self.Analytic,
            'gain': self.reserved - self.expense, # no change
        }
    
    def _test_05_results(self):
        """ (!) Amounts in budget reservations of picking are
            actually **NOT** modified if product's `standard_price`
            is modified
        """
        expense = self.product.standard_price * 2
        return {
            'other_expense_aacs': self.Analytic,
            'budget_reserved': self.reserved,
            'budgetable': expense,
            'expense_valued': expense,
            'gain': self.reserved - expense,
        }
    
    @classmethod
    def _set_expense_valued(cls, expense):
        cls.product.standard_price = expense
        cls.env.invalidate_all()

    def _test_06_results(self):
        return super()._test_06_results() | {
            'gain': self.reserved - self.expense, # no change
        }

    def _test_08_results(self):
        """ On picking, modifying analytic distribution:
            - impacts expense distribution, for sure
            - does not trigger reservation amount auto-update
              (user can do it with the button)
        """
        # 1 line has aac distrib with 2 aac on 50% and 1 on 100%
        # the 2nd line is standard at 100%
        # => UNIT_PRICE is counted 3 times
        expense = self.UNIT_PRICE * 3
        return super()._test_08_results() | {
            'budget_reserved': self.reserved,
            'budgetable': expense,
            'expense_valued': expense,
            'gain': self.reserved - expense, # -200
        }

    #===== Picking specific =====#
    def test_80_validate_picking(self):
        """ Ensure changing product's `standard_price` does not change picking expense when
            the picking is done, thanks to stock.valuation.layer (instead as in test_05)
        """
        # initial state:
        # validate the picking & change product's standard_price
        self._set_record_done()
        
        # change product's price => picking expense changes because no svl yet
        prev_expense = self.record.total_expense_valued
        self._set_expense_valued(self.UNIT_PRICE + 100.0)
        self.assertTrue(self.record.state, 'done')
        self.assertTrue(self.record[self.field_lines].stock_valuation_layer_ids)
        self.assertEqual(prev_expense, self.record.total_expense_valued)

    @classmethod
    def _set_record_done(cls):
        cls.record.action_confirm()
        cls.record[cls.field_lines].quantity_done = 1.0
        cls.record[cls.field_lines]._action_done()
