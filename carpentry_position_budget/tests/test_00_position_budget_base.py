# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command
from odoo.tests import common

from odoo.addons.carpentry_position.tests.test_carpentry_position import TestCarpentryPosition_Base

class TestCarpentryPositionBudget_Base(TestCarpentryPosition_Base):

    HOUR_COST = 30.0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # firsts of the 3
        cls.lot = fields.first(cls.project.lot_ids)
        cls.position = fields.first(cls.project.position_ids)
        cls.phase = fields.first(cls.project.phase_ids)
        cls.launch = fields.first(cls.project.launch_ids)

        # analytic
        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Project Budgets Test 01'
        })
        cls.aac_aluminium = cls.env['account.analytic.account'].create({
            # aluminium tests global costs
            'name': 'AAC Aluminium Test 01',
            'plan_id': cls.analytic_plan.id,
            'budget_type': 'project_global_cost'
        })
        cls.aac_prod = cls.env['account.analytic.account'].create({
            'name': 'AAC Production Test 01',
            'plan_id': cls.analytic_plan.id,
            'budget_type': 'production'
        })
        cls.aac_install = cls.aac_prod.copy({
            'name': 'AAC Install Test 01',
            'budget_type': 'installation'
        })

        # budget & template line
        cls.account = cls.env["account.account"].create({
            "code": "accounttest01",
            "name": "Test Account 01",
            "account_type": "asset_fixed",
        })
        cls.project.date_start = '2022-01-01' # like timesheet_cost_history_ids
        cls.budget = fields.first(cls.project.budget_ids)
        cls.TemplateLine = cls.env['account.move.budget.line.template']
        cls.TemplateLine.create([{
            'analytic_account_id': cls.aac_aluminium.id,
            'account_id': cls.account.id,
        }, {
            'analytic_account_id': cls.aac_prod.id,
            'account_id': cls.account.id,
        }, {
            'analytic_account_id': cls.aac_install.id,
            'account_id': cls.account.id,
        }])

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
            'analytic_account_id': cls.aac_aluminium.id,
        }, {
            'external_db_type': 'orgadata',
            'external_db_col': 'Fab2',
            'analytic_account_id': cls.aac_prod.id,
        }, {
            'external_db_type': 'orgadata',
            'external_db_col': 'Pose1',
            'analytic_account_id': cls.aac_install.id,
        }, {
            'external_db_type': 'orgadata',
            'external_db_col': 'Pose2',
            'analytic_account_id': cls.aac_install.id,
        }])

        # hour valuation
        # production
        cls.dpt_prod = cls.env['hr.department'].create({
            'name': 'Test Production Department 01',
            "analytic_account_id": cls.aac_prod.id,
            "hourly_cost": cls.HOUR_COST
        })
        vals = {
            "hourly_cost": cls.HOUR_COST,
            "currency_id": cls.env.user.company_id.currency_id.id,
        }
        cls.dpt_prod.timesheet_cost_history_ids = [
            Command.create(vals | {"starting_date": '2022-01-01'}),
            Command.create(vals | {"starting_date": '2023-01-01'}),
        ]
        # installation
        cls.dpt_install = cls.dpt_prod.copy({
            'name': 'Test Installation Department 01',
            'analytic_account_id': cls.aac_install.id
        })
        for history in cls.dpt_prod.timesheet_cost_history_ids:
            history.copy({'department_id': cls.dpt_install.id})
