# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command
from odoo.tests import common, new_test_user

from odoo.addons.carpentry_position.tests.test_carpentry_00_base import TestCarpentryGroup_Base

class TestCarpentryPositionBudget_Base(TestCarpentryGroup_Base):

    HOUR_COST = 30.0
    DURATION_HOURS = 5.0
    DURATION_MINUTES = DURATION_HOURS * 60

    amount_production = 20.0 # hours
    amount_installation = 10.0 # hours
    amount_other = 100.0 # €
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.CostHistory = cls.env['hr.employee.timesheet.cost.history']
        cls.BudgetLine = cls.env['account.move.budget.line']
        cls.Available = cls.env['carpentry.budget.available']
        cls.Remaining = cls.env['carpentry.budget.remaining']
        cls.Expense = cls.env['carpentry.budget.expense']

        cls.project_user = new_test_user(
            cls.env, "project_user", "project.group_project_user" # base.group_user
        )

        cls._configure_analytics()
        cls._create_budget_project()

    @classmethod
    def _create_project(cls, project_name):
        """ Add `date` and `date_start` to project's, for budget valuation """
        super()._create_project(project_name)
        cls.project.write({
            'date_start': '2022-01-01',
            'date': '2023-12-31',
        })

    @classmethod
    def _create_budget_project(cls):
        """ Add budgets when initializing project """
        # Positions' budget
        for position in cls.project.position_ids:
            cls._create_budget_position(position, cls.aac_installation, cls.amount_installation)
            cls._create_budget_position(position, cls.aac_production, cls.amount_production)
        cls.budget_installation = cls.position.position_budget_ids.filtered(lambda x: x.budget_type == 'installation')
        cls.budget_production = cls.position.position_budget_ids.filtered(lambda x: x.budget_type == 'production')

        # Project's budget (other)
        cls.project.budget_line_ids = [Command.create({
            'date': '2022-01-01',
            'budget_id': cls.project.budget_id.id,
            'analytic_account_id': cls.aac_other.id,
            'debit': cls.amount_other,
        })]

    @classmethod
    def _create_budget_position(cls, position, analytic, amount):
        position.position_budget_ids = [Command.create({
            'analytic_account_id': analytic.id,
            'amount_unitary': amount,
        })]

    @classmethod
    def _configure_analytics(cls):
        # analytic
        cls.budget_types = ('other', 'goods', 'production', 'installation', 'service')
        cls.Analytic = cls.env['account.analytic.account']
        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Project Budgets Test 01'
        })
        cls.aacs = (
            cls.Analytic.create([{
                'plan_id': cls.analytic_plan.id,
                'name': budget_type,
                'budget_type': budget_type,
            } for budget_type in cls.budget_types
        ]))
        (
            cls.aac_other, cls.aac_goods, cls.aac_production,
            cls.aac_installation, cls.aac_service
        ) = cls.aacs

        # 1 budget line template per aac
        cls.account = cls.env["account.account"].create({
            "code": "accounttest01",
            "name": "Test Account 01",
            "account_type": "asset_fixed",
        })
        cls.project.date_start = '2022-01-01' # like timesheet_cost_history_ids
        cls.budget = fields.first(cls.project.budget_ids)
        cls.TemplateLine = cls.env['account.move.budget.line.template']
        cls.TemplateLine.create([{
            'analytic_account_id': aac.id,
            'account_id': cls.account.id,
        } for aac in cls.aacs])

        # interface
        cls.Interface = cls.env['carpentry.position.budget.interface']
        (
            cls.interface_aac,
            cls.interface_fab2,
            cls.interface_pose1,
            cls.interface_pose2
        ) = cls.Interface.create([{
            'external_db_type': 'orgadata',
            'external_db_col': 'A_ACC',
            'analytic_account_id': cls.aac_other.id,
        }, {
            'external_db_type': 'orgadata',
            'external_db_col': 'Fab2',
            'analytic_account_id': cls.aac_production.id,
        }, {
            'external_db_type': 'orgadata',
            'external_db_col': 'Pose1',
            'analytic_account_id': cls.aac_installation.id,
        }, {
            'external_db_type': 'orgadata',
            'external_db_col': 'Pose2',
            'analytic_account_id': cls.aac_installation.id,
        }])

        # hour valuation (production & installation)
        cls.CostHistory.create([{
            "analytic_account_id": aac.id,
            'starting_date': '2022-01-01',
            "hourly_cost": cls.HOUR_COST,
            'currency_id': cls.project.currency_id.id,
        } for aac in (cls.aac_production, cls.aac_installation, cls.aac_service)])
