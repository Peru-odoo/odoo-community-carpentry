# -*- coding: utf-8 -*-

from odoo import Command

from odoo.addons.carpentry_position_budget.tests.test_05_analytic_project import (
    TestCarpentryPositionBudget_AnalyticBase,
)
from odoo.addons.carpentry_position_budget.tests.test_06_reservation import (
    TestCarpentryPositionBudget_Reservation,
)

class TestCarpentryTaskBudget_Base(TestCarpentryPositionBudget_AnalyticBase):
    model_section = 'project.task'
    field_section = 'task_id'
    field_lines = 'timesheet_ids'

    amount_service = 20.0 # 20h

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def _create_budget_project(cls):
        # create 'service' budget in the project
        cls.project.budget_line_ids = [Command.create({
            'date': '2022-01-01',
            'budget_id': cls.project.budget_id.id,
            'analytic_account_id': cls.aac_service.id,
            'qty_debit': cls.amount_service,
        })]

        super()._create_budget_project()

    @classmethod
    def _create_section_product(cls):
        # employees
        cls.employee = cls.env['hr.employee'].create({
            'name': 'User Empl Employee',
            'user_id': cls.env.user.id,
        })
        cls.employee.hourly_cost = cls.UNIT_PRICE

        # task type
        cls.task_type = cls.env['project.type'].create([{
            'name': 'Task Type',
            'task_ok': True,
        }])

        cls.section = cls.env['project.task'].with_user(user=cls.env.user.id).create({
            'project_id': cls.project.id,
            'name': 'Task Test',
            'type_id': cls.task_type.id,
            'analytic_account_id': cls.aac_service.id,
            'allow_timesheets': True,
            'planned_hours': cls.DURATION_HOURS,
            'timesheet_ids': [Command.create({
                'project_id': cls.project.id,
                'name': 'Timesheet line 1',
                'unit_amount': cls.DURATION_HOURS,
            })]
        })
        cls.line = cls.section.timesheet_ids

        cls.stage_closed = cls.env['project.task.type'].create({
            'name': 'Closed Stage Test',
            'fold': True,
        })

class TestCarpentryTaskBudget_Reservation(
    TestCarpentryPositionBudget_Reservation,
    TestCarpentryTaskBudget_Base,
):
    @classmethod
    def setUpClass(cls):
        super(TestCarpentryTaskBudget_Reservation, cls).setUpClass()

    @classmethod
    def _print_debug(cls):
        print('hourly_costs', cls.env['carpentry.budget.hourly.cost'].search_read(
            [('analytic_account_id', '=', cls.aac_service.id)],
            ['budget_type', 'coef']
        ))
        print('expense', cls.env['carpentry.budget.expense'].search_read(
            [('section_id', '=', cls.section.id)],
            ['amount_reserved', 'amount_reserved_valued', 'amount_expense', 'amount_expense_valued', 'analytic_account_id']
        ))
        print('lines', cls.env['account.analytic.line'].search_read(
            [('account_id', '=', cls.aac_service.id)],
            ['unit_amount', 'amount', 'user_id']
        ))
        print('section', cls.section.read(['is_closed', 'effective_hours', 'planned_hours', 'total_budget_reserved']))
        print('reservations', cls.section.reservation_ids.read(['analytic_account_id', 'amount_reserved']))
        print('self.amount_service', cls.amount_service)
        print('self.line.unit_amount', cls.line.unit_amount)

    #===== Auto/suggestion mode =====#
    # See `carpentry_position_budget/TestCarpentryPositionBudget_Reservation`
    def test_01_auto_budget_project(self):
        """ Most standard case:
            * planned hours == budget reservation (enough budget)
            * task still opened
            * timesheets < reserved budget & planned hours

            => No gain until task isn't closed.
            => Loss as soon as timesheets > reserved budget & planned hours (test05)
        """
        self.assertEqual(self.section.effective_hours, self.DURATION_HOURS)
        self._test_reservation('01')
        
    def _test_01_results(self):
        return {
            'count': 1,
            'aacs': self.aac_service,
            'launchs': self.env['carpentry.group.launch'],
            'other_expenses_aacs': self.Analytic,
            'budgetable': self.DURATION_HOURS,
            'budget_reserved': self.DURATION_HOURS,
            'expense_valued': self.DURATION_HOURS * self.UNIT_PRICE,
            'gain': (
                self.DURATION_HOURS * (self.HOUR_COST - self.UNIT_PRICE)
            ),
        }
    
    def _test_03_results(self):
        """ Non-sense for tasks (single budget) """
        return self.last_kwargs
    
    #===== Manual mode =====#
    def test_04_manual_budget_add_available(self):
        """ Non-sense for tasks (single budget) """
        return
    
    def test_05_exceeding_expense(self):
        super().test_05_exceeding_expense()
        self._set_expense_valued(self.DURATION_HOURS * self.UNIT_PRICE) # clean
    
    @classmethod
    def _set_expense_valued(cls, expense):
        cls.line.unit_amount = expense / cls.UNIT_PRICE
        cls.env.invalidate_all()
    
    def _test_05_results(self):
        """ Same than 01 with timesheets went higher than budget => loss """
        return {
            'other_expenses_aacs': self.Analytic,
            'budget_reserved': self.DURATION_HOURS,
            'budgetable': self.DURATION_HOURS, # budgetable is `planned_hours`, not expense
            'expense_valued': self.line.unit_amount * self.UNIT_PRICE,
            'gain': (
                self.section.planned_hours * self.HOUR_COST
                - self.line.unit_amount * self.UNIT_PRICE
            ), # negative => loss
        }
    
    def test_06_manual_budget_remove(self):
        self.section.analytic_account_id = False
        self._test_reservation('06')
    def _test_06_results(self):
        return {
            'count': 0,
            'aacs': self.Analytic,
            'other_expenses_aacs': self.Analytic, # timesheets are on task's analytic -> empty here
            'budget_reserved': 0.0,
            'budgetable': self.line.unit_amount,
            'expense_valued': self.line.unit_amount * self.UNIT_PRICE,
            'gain': -1 * self.line.unit_amount * self.UNIT_PRICE,
        }

    def test_08_unknown_expense(self):
        """ When an employee of a different budget than the task's one
            logs timesheet lines => no `other_expense_ids` is generated,
            else all expense is set to task' analytic
            (with different hour_cost per employee/department)

            This just follows native behavior, no test needed
        """
        return
    
    #===== Task specific =====#
    def test_20_budget_from_launch(self):
        """ Change to `aac_installation` which needs launchs on tasks to
            form budget reservation matrix
        """
        self.section.write({
            'launch_ids': False,
            'analytic_account_id': self.aac_installation.id,
        })
        self._test_reservation_values(
            count=0,
            aacs=self.Analytic,
            budget_reserved=0.0,
        )

        self.section.write({
            'launch_ids': self.launch.ids,
            'planned_hours': self.DURATION_HOURS,
        })
        self._test_reservation_values(
            count=1,
            aacs=self.aac_installation,
            budget_reserved=self.DURATION_HOURS,
        )

    def test_21_task_without_timesheets(self):
        """ Ensure the budget reservation still forms well (like on new task) """
        new_task = self.section.copy({
            'planned_hours': 1.0,
            'timesheet_ids': False,
            'analytic_account_id': self.aac_service.id,
        })
        self.assertEqual(len(new_task.reservation_ids), 1)
        new_task.unlink()

    #===== Tasks `amount_reserved` & `gain` custom logics in SQL view =====#
    def test_51_opened_planned_hours_above_budget(self):
        """ User raised `planned_hours` above task budget reservation
            while task isn't closed, either:
            - because there's not enough budget, but user wants to define an objective
              for the timesheets
            - to raise already a planned loss in budget report

            => budget_reserved is thresholded at effective_hours
               - 1.0 already declared loss
        """
        self.section.write({
            'analytic_account_id': self.aac_service.id,
            'planned_hours': self.amount_service + 1.0, # 1h loss
        })
        self._test_reservation('51')
    def _test_51_results(self):
        reserved = self.DURATION_HOURS - 1.0
        return {
            'count': 1,
            'aacs': self.aac_service,
            'budget_reserved': reserved,
            'budgetable': self.amount_service + 1.0,
            'expense_valued': self.line.unit_amount * self.UNIT_PRICE,
            'gain': (
                reserved * self.HOUR_COST
                - self.DURATION_HOURS * self.UNIT_PRICE
            ),
        }

    def test_52_opened_planned_and_effective_hours_above_budget(self):
        """ Same than previous but **ALSO** timesheets is higher than budget
            => budget_reserved is at its max
            => loss only normally
        """
        self._set_expense_valued(10000 * self.UNIT_PRICE)
        self._test_reservation('52')
    def _test_52_results(self):
        reserved = self.amount_service
        return {
            'budget_reserved': reserved,
            'budgetable': self.section.planned_hours,
            'expense_valued': 10000 * self.UNIT_PRICE,
            'gain': (
                reserved * self.HOUR_COST
                - 10000 * self.UNIT_PRICE
            ),
        }
    
    def test_53_opened_planned_hours_below_budget(self):
        """ Similar than 51 but user wants to declare a gain
            by reserving more budget than `planned_hours`
            (or lowing `planned_hours` below budget)
        """
        self._set_expense_valued(self.DURATION_HOURS * self.UNIT_PRICE)
        self.section.planned_hours = self.amount_service - 5.0
        self.section.reservation_ids.amount_reserved = self.amount_service
        self._test_reservation('53')
    def _test_53_results(self):
        reserved = self.DURATION_HOURS + 5.0
        return {
            'budget_reserved': reserved,
            'budgetable': self.amount_service - 5.0,
            'expense_valued': self.DURATION_HOURS * self.UNIT_PRICE,
            'gain': (
                reserved * self.HOUR_COST
                - self.DURATION_HOURS * self.UNIT_PRICE
            ),
        }
    
    def test_54_opened_planned_hours_below_budget(self):
        """ User was too optimistic: timesheets went
            1. first, above the `planned_hours`
            2. then, also above the `sum(amount_reserved)`

            => if the 2 cases, the forecasted gain/loss is canceled
            (go back to normal)
        """
        expense_brut = self.section.planned_hours + 3.0
        self._set_expense_valued(expense_brut * self.UNIT_PRICE)
        self._test_reservation('54', expense_brut=expense_brut)

        expense_brut = 10000
        self._set_expense_valued(expense_brut * self.UNIT_PRICE)
        self._test_reservation('54', expense_brut=expense_brut)

    def _test_54_results(self, expense_brut):
        budget_brut = min(self.amount_service, expense_brut)
        expense = expense_brut * self.UNIT_PRICE
        return {
            'budget_reserved': budget_brut, # at its max
            'budgetable': self.section.planned_hours,
            'expense_valued': expense,
            'gain': (
                budget_brut * self.HOUR_COST - expense
            ),
        }
    
    def test_55_closed_loss(self):
        """ Closed while timesheets > `sum(amount_reserved)`:
            (no matter `planned_hours`)
            => no change
        """
        self.section.stage_id = self.stage_closed
        self._test_reservation_idem()

    
    def test_56_closed_gain(self):
        """ Closed while timesheets < `sum(amount_reserved)`:
            (no matter `planned_hours`)
            => generates gain!
        """
        self.section.planned_hours = self.amount_service - 5.0
        self._set_expense_valued(self.DURATION_HOURS * self.UNIT_PRICE)
        self._test_reservation('56')
    def _test_56_results(self):
        budget_brut = self.amount_service - 5.0
        expense = self.DURATION_HOURS * self.UNIT_PRICE
        return {
            'budget_reserved': budget_brut, # at its max
            'budgetable': budget_brut,
            'expense_valued': expense,
            'gain': (
                budget_brut * self.HOUR_COST - expense
            ),
        }
