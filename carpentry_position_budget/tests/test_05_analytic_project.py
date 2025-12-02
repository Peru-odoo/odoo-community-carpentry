# -*- coding: utf-8 -*-

from odoo import exceptions, fields, _, Command

from .test_00_position_budget_base import TestCarpentryPositionBudget_Base

class TestCarpentryPositionBudget_AnalyticBase(TestCarpentryPositionBudget_Base):
    """ Help/tool class for budgets tests """

    # configuration for inheriting modules
    UNIT_PRICE = 150.0
    record_model = None # like 'purchase.order'
    field_lines = None # like 'order_line'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        if cls.record_model:
            cls.Model = cls.env[cls.record_model]
            if cls.field_lines:
                cls.model_line = cls.env[cls.record_model][cls.field_lines]._name
                cls.Line = cls.env[cls.model_line]
        
        # other projects to play changes with
        cls.project2 = cls.Project.create({'name': 'Project2'})
        cls.project3 = cls.Project.create({'name': 'Project3'})

        cls.project_aac = cls.project.analytic_account_id
        cls.project2_aac = cls.project2.analytic_account_id
        cls.project3_aac = cls.project3.analytic_account_id

        cls._create_record_product()

    @classmethod
    def _create_record_product(cls):
        if not cls.record_model: return

        # journal (for account.move & purchase)
        cls.account, _ = cls.env['account.account'].create([{
            'code': '601000',
            'name': 'Direct purchase',
            'account_type': 'expense',
        },{
            'code': '401100', # for po -> invoice
            'name': 'Provider debt',
            'account_type': 'liability_payable',
        }])
        cls.journal = cls.env['account.journal'].create({
            'name': 'Test Journal',
            'code': 'JRN',
            'type': 'purchase',
            'default_account_id': cls.account.id, # for po -> invoice
        })

        # product
        vals = {
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
            'standard_price': cls.UNIT_PRICE,
            'property_account_expense_id': cls.account.id, # for po -> invoice
        }
        cls.product, cls.product_storable = cls.env['product.product'].create([
            {'name': 'Product Consumable', 'type': 'consu'}   | vals,
            {'name': 'Product Storable',   'type': 'product'} | vals,
        ])

        # analytic distribution model
        cls.distrib_model = cls.env['account.analytic.distribution.model'].create([{
            'product_id': cls.product.id,
            'analytic_distribution': {
                cls.aac_other.id: 50,
                cls.aac_installation.id: 50,
            }
        }])
    
        # record
        cls.record = cls.env[cls.record_model].create(cls._get_vals_record())
        if cls.field_lines:
            cls.record[cls.field_lines] = [
                Command.create(cls._get_vals_new_line()),
                Command.create(cls._get_vals_new_line(cls.product_storable)),
            ]
            cls.line, cls.line_storable = cls.record[cls.field_lines]

        #==== For Enforcement ====#
        company = cls.env.user.company_id
        cls.project_internal = hasattr(company, 'internal_project_id') and company.internal_project_id
    
    @classmethod
    def _get_vals_record(cls):
        return {
            'project_id': cls.project.id,
            'partner_id': cls.env.user.partner_id.id,
        }
    
    @classmethod
    def _get_vals_new_line(cls, product=None, qty=1.0):
        return {
            'product_id': product.id if product else cls.product.id,
            'product_qty': qty,
            'price_unit': cls.UNIT_PRICE,
        }

    @classmethod
    def _add_analytic(cls, new_distrib, line=None):
        line = line or cls.line
        distrib = line.analytic_distribution or {}
        line.analytic_distribution = distrib | new_distrib
    

    def _test_line_projects(self, projects, equal=True, line=None):
        """ Helper/tool method: test if projects' analytics are in line's distribution """
        line = line or self.line
        testMethod = self.assertEqual if equal else self.assertNotEqual

        mapped_project_analytics = line._get_mapped_projects_analytics()
        projects_analytics = line._get_analytics_projects(mapped_project_analytics)

        debug = False
        if debug:
            print('line.analytic_distribution', line.analytic_distribution)
            print('projects_analytics', projects_analytics)
            print('project_aac', self.project_aac)
            print('project2_aac', self.project2_aac)
            print('project3_aac', self.project3_aac)
        
        testMethod(
            projects_analytics, # from analytic distrib
            set(projects.analytic_account_id.ids)
        )

class TestCarpentryPositionBudget_AnalyticProject(TestCarpentryPositionBudget_AnalyticBase):
    """ This test Class is mostly not executed in this module but designed
        to be inherited by `carpentry_..._budget` modules

        It tests logics of `analytic.mixin`
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    #===== account.analytic.account =====#
    def test_01_budget_line_type(self):
        """ Tests `account_analytic_account._get_default_line_type()` """
        self.assertEqual(self.aac_goods       ._get_default_line_type(), 'amount')
        self.assertEqual(self.aac_installation._get_default_line_type(), 'workforce')
        self.assertTrue('workforce' in self.project.budget_line_ids.mapped('type'))

    #===== Line's project computation logics: from `analytic_distribution` then *record* =====#
    def test_02_line_initial_project(self):
        """ Ensure when created by ORM, project is correctly cascade to the line """
        if not self.record_model: return

        self._test_line_projects(self.project)

    def test_03_line_project_follows_on_record_change(self):
        """ Change record's project: line's project should follow """
        if not self.record_model: return

        # change the project
        self.record.project_id = self.project2
        self._test_line_projects(self.project2)

    def __old_test_04_remove_line_analytic(self):
        """ **LEGACY** Logics of record's project cascade to line's analytic
             is not triggered anymore on analytic distrib' change, to let user
             modify it, e.g. to multiple project or even different project than
             record

            Remove line's analytic: line's project should
            fallback to record's project immediatly
        """
        if not self.record_model: return

        distrib = self.line.analytic_distribution
        distrib.pop(str(self.project2_aac.id))
        self.line.analytic_distribution = distrib

        self._test_line_projects(self.project2)
    
    def test_05_set_line_analytic_different_to_record(self):
        """ Simulate that user sets a different project analytic
            on line's distrib than record's: this should be kept
        """
        if not self.record_model: return

        distrib = self.line.analytic_distribution
        distrib.pop(str(self.record.project_id.analytic_account_id.id))
        distrib |= {self.project3_aac.id: 100}
        self.line.analytic_distribution = distrib

        # priority on project from analytic distribution over record's
        self._test_line_projects(self.project3)
        self._test_line_projects(self.record.project_id, equal=False)
    
    def test_06_non_persistent_line_analytic(self):
        """ Change record's project while line is on different analytic:
            line's analytic should *not resist*: record's project should cascade
        """
        if not self.record_model: return

        self.record.project_id = self.project
        self._test_line_projects(self.project)

    def __old_test_07_remove_line_analytic_from_different_project(self):
        """ **LEGACY**
            Same than a previous test but line with originally different project than record's
        """
        if not self.record_model: return

        distrib = self.line.analytic_distribution
        distrib.pop(str(self.project3_aac.id))
        self.line.analytic_distribution = distrib

        self._test_line_projects(self.project)

    # ===== Multiple project distribution =====#
    def test_08_update_record_project_multiple_distribution(self):
        """ Ensure than in multiple project distribution done by user,
            **all** projects analytics is replaced by record's one
        """
        if not self.record_model: return

        # ensure start state: record is on 'project', line is on 'project' and 'project2'
        self._add_analytic({self.project2_aac.id: 100})
        self.assertEqual(self.record.project_id, self.project)
        self._test_line_projects(self.project + self.project2)

        # change record's project: line should align *only* to record
        self.record.project_id = self.project3
        self._test_line_projects(self.project3)
        
        # same test, but with start state (projects 2 and 3) containing the target's project (project2)
        self._add_analytic({self.project2_aac.id: 100})
        self.record.project_id = self.project2
        self._test_line_projects(self.project2)

    #===== New line =====#
    def test_10_new_line_create(self):
        """ Ensure new lines follows record's project """
        if not self.record_model or not self.field_lines: return
        
        # create new line: it should follow record's project
        self.record[self.field_lines] = [Command.create(self._get_vals_new_line(qty=5.0))]
        new_line = self.record[self.field_lines][-1]
        self._test_line_projects(self.record.project_id, line=new_line)

    #===== Other analytic plans =====#
    def test_11_line_other_analytic_is_kept(self):
        """ Ensure analytics of other plans (like budgets) were not touched by project changes """
        if not self.record_model: return
        
        self.assertTrue(
            str(self.aac_other.id) in self.line.analytic_distribution.keys()
        )

class TestCarpentryPositionBudget_AnalyticEnforcement(TestCarpentryPositionBudget_AnalyticBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def _should_test_enforcement(cls):
        """ Just a shortcut/tool method
        
            Can also be inherited to cancel and re-write next tests,
            if *internal* enforcement rules is different than the native
        """
        return (
            bool(cls.record_model) and
            bool(cls.project_internal) and
            hasattr(cls.Line, '_should_enforce_internal_analytic')
        )

    def test_01_enforce_storable_to_internal_project(self):
        """ Ensure analytic enforcement to *INTERNAL* project """
        if not self._should_test_enforcement(): return

        self._test_line_projects(self.project_internal, line=self.line_storable)

        # try and change line's analytic: it should be enforced to internal project
        self.line_storable.analytic_distribution |= {self.project2_aac.id: 100}
        self._test_line_projects(self.project2,         line=self.line_storable, equal=False)
        self._test_line_projects(self.project_internal, line=self.line_storable)

    def test_02_enforce_resist_on_record_project_change(self):
        """ Test that changing record's project keeps enforcement """
        if not self._should_test_enforcement(): return
        
        self.record.project_id = self.project3
        self._test_line_projects(self.project3,         line=self.line_storable, equal=False)
        self._test_line_projects(self.project_internal, line=self.line_storable)

    def test_03_stop_to_enforce(self):
        """ Ensure analytic switch back to record's when removing enforcment """
        if not self._should_test_enforcement(): return

        # change line's product to consummable => line's project should follow back record's
        self.line_storable.product_id = self.product
        self._test_line_projects(self.record.project_id, line=self.line_storable)

    def test_04_enforce_on_product_change(self):
        """ Ensure existing line is enforced when changing product """
        if not self._should_test_enforcement(): return

        # change line's product to consummable => line's project should follow back record's
        self.line.product_id = self.product_storable
        self._test_line_projects(self.project_internal)
