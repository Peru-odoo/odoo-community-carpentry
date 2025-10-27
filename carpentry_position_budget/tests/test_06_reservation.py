# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command

from .test_05_analytic_project import TestCarpentryPositionBudget_AnalyticBase

class TestCarpentryPositionBudget_Reservation(TestCarpentryPositionBudget_AnalyticBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.last_kwargs = {}
    
    @classmethod
    def _create_section_product(cls):
        cls._quick_affect() # affect all budget to launch1
        super()._create_section_product()

    #===== Helper method =====#
    @classmethod
    def _print_section_debug(cls):
        debug = False
        if debug:
            print('analytics', cls.section.budget_analytic_ids.read(['name']))
            print('analytic_distribution', cls.section[cls.field_lines].read(['product_id', 'analytic_distribution']))
            print('product_id', cls.section[cls.field_lines].product_id.read(['standard_price']))

    def _test_reservation(self, code, **kwargs_results):
        """ Call `_test_reservation_values` with the expected results
            fetch from the method `_test_reservation_results_[code]`
        """
        method = '_test_' + code + '_results'
        if hasattr(self, method):
            kwargs_values = getattr(self, method)(**kwargs_results)
            if kwargs_values:
                self._test_reservation_values(**kwargs_values)

    def _test_reservation_values(self, **kwargs):
        """ Shortcut to test count, aac, launch & amount of reservations """
        reservations = self.section.reservation_ids

        debug = True
        if debug:
            print(' == _test_reservation_values == ')
            self._print_section_debug()
            print('reservations', reservations.read(['launch_id', 'analytic_account_id', 'amount_reserved']))

        # reservations
        if 'count' in kwargs:
            self.assertEqual(len(reservations), kwargs['count'])
        if 'aacs' in kwargs:
            self.assertEqual(reservations.analytic_account_id, kwargs['aacs'])
        if 'launchs' in kwargs:
            self.assertEqual(reservations.launch_id, kwargs['launchs'])
        if 'other_expenses_aacs' in kwargs:
            self.assertEqual(
                self.section.other_expense_ids.analytic_account_id,
                kwargs['other_expenses_aacs'],
            )

        # amounts
        fields = [
            ('budget_reserved', 'total'),
            ('budgetable',      'total'),
            ('expense_valued',  'total'),
            ('gain',            'amount'),
        ]
        for (kwarg, prefix) in fields:
            if not kwarg in kwargs:
                continue
            if debug:
                print('kwarg', kwarg)
            self.assertEqual(
                # `round` is good enough here, we're not testing precision
                round(self.section[prefix + '_' + kwarg]), round(kwargs[kwarg])
            )
        
        self._save_last_kwargs(kwargs)
    
    def _test_reservation_idem(self):
        """ Quick way to test nothing has changed """
        if self.last_kwargs:
            self._test_reservation_values(**self.last_kwargs)
    
    @classmethod
    def _save_last_kwargs(cls, kwargs):
        cls.last_kwargs = kwargs

    #===== Auto/suggestion mode =====#
    def test_01_auto_budget_project(self):
        """ Ensure when adding real expenses (like products),
            budget & reservations are automatically selected/created
        """
        if not self.model_section: return

        # 2 budgets automatically selected (because in product's analytic distrib)...
        # print('self.section.project', self.section.project_id)
        self.assertEqual(
            self.section.budget_analytic_ids,
            self.aac_other + self.aac_installation,
        )

        # but only 1 affectation (because `installation` from launch and none selected)
        self._test_reservation('01')

    def test_02_auto_budget_add_launch_empty(self):
        """ Test adding a launch with no budget replay auto-reservation
            but does change anything
        """
        if not self.model_section: return

        # launch2 has no budget: should not change anything
        self.section.reservation_ids.amount_reserved = 0.0
        self.section.launch_ids = self.launchs[1]
        self._test_reservation_idem()

    def test_03_auto_budget_add_launch(self):
        """ launch1 has `installation` and `production` budget:
            `installation` should be added (in distrib model of cls.product)
        """
        if not self.model_section: return

        self.section.launch_ids |= self.launch
        self._test_reservation('03')
    
    #===== Manual mode =====#
    def test_04_manual_budget_add_available(self):
        """ Ensure when adding a new budget center manually,
            previous and new one are all kept,
            and that reservations lines & expense distribution are recomputed
        """
        if not self.model_section: return

        # user updates reservation amount: nothing should happen to budget_analytic_ids
        resa_install = self.section.reservation_ids.filtered(
            lambda x: x.analytic_account_id == self.aac_installation
        )
        resa_install.amount_reserved = 0.0
        self.assertEqual(
            self.section.budget_analytic_ids,
            self.aac_other + self.aac_installation,
        )

        # user adds budget (available but with no expense):
        # it should be kept, and reservation should be recomputed
        self.section.budget_analytic_ids |= self.aac_production
        all_aacs = self.aac_other + self.aac_installation + self.aac_production
        self.assertEqual(self.section.budget_analytic_ids, all_aacs)
        self._test_reservation('04', all_aacs=all_aacs)

    def test_05_exceeding_expense(self):
        """ Ensure loss is generated when expense > available """
        if not self.model_section: return

        # not enough budget for the expense
        expense = self.UNIT_PRICE * 10000 # 150*10 000 = 1 500 000
        self._set_expense_valued(expense)
        self._test_reservation('05')

        # clean
        self._set_expense_valued(self.UNIT_PRICE)
    
    @classmethod
    def _set_expense_valued(cls, expense):
        """ Ok for PO, but inheritted for picking (product_id.standard_price) """
        cls.line.price_unit = expense
    
    def test_06_manual_budget_remove(self):
        """ Ensure manually removing budgets works """
        if not self.model_section: return

        self.section.budget_analytic_ids -= self.aac_production
        self._test_reservation('06')
    
    def _test_06_results(self):
        return {
            'count': 2,
            'aacs': self.aac_other + self.aac_installation,
            'other_expenses_aacs': self.Analytic,
        }
    
    # def test_07_multiple_project_splitted_expense(self):
    #     """ Test an expense is counted on the projects of its
    #         analytic distribution, especially in case of multiple
    #         project distribution
    #     """
    #     # TODO @arnaudlayec
    #     if not self.model_section: return

    #     # initial state: expense on 2 budgets, 1 project
    #     domain = [('section_id', '=', self.section.id), ('section_res_model', '=', self.section._name)]
    #     expenses = self.Expense.with_context(active_test=False).search(domain)
    #     print('expense_multiple', expenses.read([]))
    #     self.assertEqual(len(expenses), 2)
    #     self.assertEqual(expenses.project_id, self.project)

    #     # multiple projects: 2 budgets * 2 projects => 4 expenses lines
    #     self.line.analytic_distribution |= {self.project2_aac.id: 100}
    #     expenses = self.Expense.with_context(active_test=False).search(domain)
    #     self.assertEqual(len(expenses), 4)
    #     self.assertEqual(expenses.project_id, self.project + self.project2)

    def test_08_unknown_expense(self):
        """ Add expense of a unknown budget in the project """
        if not self.model_section: return

        # setup: put expense on unknown budget in the project
        self.line.analytic_distribution |= {self.aac_goods.id: 100}
        self._test_reservation('08')

    def _test_08_results(self):
        return {
            'count': 2,
            'aacs': self.aac_other + self.aac_installation, # not in project => not added in budget_analytic_ids
            'other_expenses_aacs': self.aac_goods, # not in reservations (because not available, or here, not in project) => in other expense
        }
    
    #===== Other & UI =====#
    def test_09_reservation_fields_from_section(self):
        """ Ensure that section fields cascade to reservations, for: sequence, budget_date, active """
        if not self.model_section or not self.section.reservation_ids:
            return

        if hasattr(self.section, 'sequence'):
            self.section.sequence = 99
            self.assertEqual(set(self.section.reservation_ids.mapped('sequence_section')), {99})

        if hasattr(self.section, 'active'):
            self.section.active = False
            self.assertEqual(set(self.section.reservation_ids.mapped('active')), {False})
            self.section.active = True

    def test_10_readonly_reservation_budget(self):
        """ Ensure either budget center choice (left), either reservation table (right)
            are readonly as soon as 1 modification needs a *flush* (save)
        """
        if not self.model_section: return
