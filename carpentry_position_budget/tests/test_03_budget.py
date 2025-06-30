# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command
from odoo.tests import common, Form

from odoo.tools import file_open
import base64

from .test_00_position_budget_base import TestCarpentryPositionBudget_Base

class TestCarpentryPositionBudget_Budget(TestCarpentryPositionBudget_Base):

    BUDGET_ALUMINIUM = 100.0 # euros
    budget_production = 20.0 # hours
    budget_installation = 10.0 # hours

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Each project's position: add Prod and Install budgets (keep Aluminium for unit line)
        for position in cls.project.position_ids:
            cls._add_budget(position, cls.aac_install, cls.budget_installation)
            cls._add_budget(position, cls.aac_prod, cls.budget_production)

    def _add_budget(position, analytic, amount):
        position.position_budget_ids = [Command.create({
            'analytic_account_id': analytic.id,
            'amount': amount
        })]


    # def test_01_position_unitary_budget(self):
    #     """ Test totals on position """
    #     brut, valued = self.position.position_budget_ids._get_position_unitary_budget(
    #         groupby_budget='budget_type',
    #         brut_or_valued='both',
    #     )
    #     self.assertEqual(brut.get(self.position.id), {
    #         'installation': self.budget_installation,
    #         'production': self.budget_production,
    #     })
    #     self.assertEqual(valued.get(self.position.id), {
    #         'installation': self.budget_installation * self.HOUR_COST,
    #         'production': self.budget_production * self.HOUR_COST,
    #     })

    def test_02_position_subtotal(self):
        subtotal = (
            + self.budget_production * self.HOUR_COST
            + self.budget_installation * self.HOUR_COST
        )
        self.assertEqual(self.position.budget_subtotal, subtotal)
    

    def test_03a_budget_line_type(self):
        """ Tests `account_analytic_account._get_default_line_type()` """
        self.assertEqual(self.aac_install._get_default_line_type(), 'workforce')
        self.assertEqual(set(self.project.budget_line_ids.mapped('type')), {'workforce'})

    def test_03b_project_budget_change_valuation(self):
        """ Test that project total changes on valuation changes"""
        position_budget_id = self.position.position_budget_ids.filtered(lambda x: x.analytic_account_id == self.aac_prod)

        project_total = self.project.budget_total
        position_prod = position_budget_id.value

        history_entry = fields.first(self.dpt_prod.timesheet_cost_history_ids)
        history_entry.hourly_cost = self.HOUR_COST + 1.0

        self.assertNotEqual(position_budget_id.value, position_prod)
        self.assertNotEqual(self.project.budget_total, project_total)

    def test_04_project_budget_change_position_qty(self):
        """ Test that project total changes on position qty changes"""
        total = self.project.budget_total
        self.position.quantity = 10
        self.assertNotEqual(self.project.budget_total, total)

    def test_05_project_budget_change_unit_line(self):
        """ Test that project total changes when adding manual
            global cost to the budget
        """
        total = self.project.budget_total
        self.budget.line_ids = [Command.create({
            'name': 'Line test 01',
            'date': self.budget.date_from,
            'debit': 100.0,
            'analytic_account_id': self.aac_aluminium.id,
            'account_id': self.account.id,
        })]
        self.assertEqual(self.project.budget_total, total + 100.0)

    def test_06_project_budget_line_update(self):
        """ Auto-removal of lines in project budget when removing positions' budgets """
        nb_lines = len(self.project.budget_line_ids.ids)
        domain = [('analytic_account_id', '=', self.aac_prod.id)]
        self.project.position_budget_ids.search(domain).unlink()

        self.assertEqual(len(self.project.budget_line_ids.ids), nb_lines-1)


    def test_07_phase_budget(self):
        # Ensure a clean base to start
        self.Affectation.search([('project_id', '=', self.project.id)]).unlink()
        self.assertFalse(self.phase.budget_installation)
        
        position2 = self.project.position_ids[1]
        self._write_affect(self.phase, position2, {'quantity_affected': 2})
        self.assertEqual(
            self.phase.budget_installation,
            self.budget_installation * 2
        )

    def test_08_launch_budget(self):
        self.assertFalse(self.launch.budget_installation)

        position2 = self.project.position_ids[1]
        self._write_affect(self.launch, self.project.phase_ids.affectation_ids[0])
        self.assertEqual(
            self.launch.budget_installation,
            self.phase.budget_installation
        )
