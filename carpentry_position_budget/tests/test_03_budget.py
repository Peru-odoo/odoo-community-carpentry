# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command
from odoo.tests import common, Form

from odoo.tools import file_open
import base64

from .test_00_position_budget_base import TestCarpentryPositionBudget_Base

class TestCarpentryPositionBudget_Import(TestCarpentryPositionBudget_Base):

    BUDGET_ALUMINIUM = 100.0 # euros
    BUDGET_PROD = 20.0 # hours
    BUDGET_INSTALL = 10.0 # hours

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Each project's position: add some Aluminium, Prod and Install budgets
        for position in cls.project.position_ids:
            cls._add_budget(position, cls.aac_aluminium, cls.BUDGET_ALUMINIUM)
            cls._add_budget(position, cls.aac_install, cls.BUDGET_INSTALL)
            cls._add_budget(position, cls.aac_prod, cls.BUDGET_PROD)

    def _add_budget(self, position, analytic, amount):
        position.position_budget_ids = [Command.create({
            'analytic_account_id': analytic.id,
            'amount': amount
        })]


    def test_01_position_unitary_budget(self):
        """ Test totals on position """
        brut, valued = self.position.position_budget_ids._get_position_unitary_budget()
        self.assertEqual(brut, {
            'consu': BUDGET_ALUMINIUM,
            'service_prod': BUDGET_PROD,
            'service_install': BUDGET_INSTALL
        })
        self.assertEqual(valued, {
            'consu': BUDGET_ALUMINIUM,
            'service_prod': BUDGET_PROD * self.HOUR_COST,
            'service_install': BUDGET_INSTALL * self.HOUR_COST
        })

    def test_01_position_subtotal(self):
        subtotal = (
            self.BUDGET_ALUMINIUM
            + self.BUDGET_PROD * self.HOUR_COST
            + self.BUDGET_INSTALL * self.HOUR_COST
        )
        self.assertEqual(self.position.budget_subtotal, subtotal)
    