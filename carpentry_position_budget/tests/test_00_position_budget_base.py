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

        # product
        cls.product_aluminium = cls.env['product.template'].create({
            'name': 'Aluminium Test 01',
            'detailed_type': 'consu',
            'budget_ok': True
        })
        cls.product_prod = cls.env['product.template'].create({
            'name': 'Production Test 01',
            'detailed_type': 'service_prod',
            'uom_id': cls.env.ref('uom.product_uom_hour').id,
            'uom_po_id': cls.env.ref('uom.product_uom_hour').id,
            'budget_ok': True,
        })
        cls.product_install = cls.product_prod.copy({
            'name': 'Install Test 01',
            'detailed_type': 'service_install',
        })

        # analytic
        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Project Budgets Test 01'
        })
        cls.aac_aluminium = cls.env['account.analytic.account'].create({
            'name': 'AAC Aluminium Test 01',
            'plan_id': cls.analytic_plan.id,
            'product_tmpl_id': cls.product_aluminium.id
        })
        cls.aac_prod = cls.env['account.analytic.account'].create({
            'name': 'AAC Production Test 01',
            'plan_id': cls.analytic_plan.id,
            'product_tmpl_id': cls.product_prod.id
        })
        cls.aac_install = cls.aac_prod.copy({
            'name': 'AAC Install Test 01',
            'product_tmpl_id': cls.product_install.id
        })

        # interface
        cls.Interface = cls.env['carpentry.position.budget.interface']
        cls.Interface.create([{
            'external_db_type': 'orgadata',
            'external_db_col': 'Fab alu',
            'analytic_account_id': cls.aac_prod.id,
        }, {
            'external_db_type': 'orgadata',
            'external_db_col': 'Pose',
            'analytic_account_id': cls.aac_install.id,
        }, {
            'external_db_type': 'orgadata',
            'external_db_col': 'Pose chantier',
            'analytic_account_id': cls.aac_install.id,
        }])


        # hour valuation
        cls.budget = fields.first(cls.project.budget_ids)
        # Attribute
        ProductAttribute = cls.env['product.attribute']
        cls.attribute = ProductAttribute.create({
            'name': 'Year test',
            'values_date_ranged': True,
            'value_ids': [Command.create({'name': y, 'date_from': y + '-01-01'}) for y in ['2022', '2023']]
        })
        # Product Template: variant creation
        attribute_line_ids = [Command.create({
            'attribute_id': cls.attribute.id,
            'value_ids': [Command.set(cls.attribute.value_ids.ids)],
        })]
        cls.product_prod.attribute_line_ids = attribute_line_ids
        cls.product_install.attribute_line_ids = attribute_line_ids
        # Variants
        cls.product_prod_2022, cls.product_prod_2023 = cls.product_prod.product_variant_ids
        cls.product_install_2022, cls.product_install_2023 = cls.product_install.product_variant_ids
        cls.product_prod_2022.standard_price = cls.HOUR_COST
        cls.product_prod_2023.standard_price = cls.HOUR_COST
        cls.product_install_2022.standard_price = cls.HOUR_COST
        cls.product_install_2023.standard_price = cls.HOUR_COST
