# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.tools import float_is_zero, float_compare

from collections import defaultdict

class CarpentryPositionBudgetImportWizard(models.TransientModel):
    _name = "carpentry.position.budget.import.wizard"
    _description = "Carpentry Position Budget Import Wizard"
    _inherit = ['utilities.file.mixin', 'utilities.database.mixin']

    #===== Fields' methods =====#
    def _selection_external_db_type(self):
        return self.env['carpentry.position.budget.interface']._selection_external_db_type()

    #===== Fields =====#
    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Project',
        readonly=True,
        default=lambda self: self.env['project.default.mixin']._get_project_id()
    )
    import_file = fields.Binary(
        string='External DB file'
    )
    filename = fields.Char(
        string='Filename'
    )

    external_db_type = fields.Selection(
        selection=_selection_external_db_type,
        string='Type of external database',
        default=lambda self: self._selection_external_db_type()[0][0],
        required=True,
    )
    encoding = fields.Selection(
        selection=[
            ('utf-8', 'UTF-8'),
            ('utf-16', 'UTF-16'),
            ('iso-8859-1', 'ISO-8859-1'),
        ],
        string='Encoding',
        default='utf-8',
        required=True,
    )

    #===== Button =====#
    def button_truncate_budget(self):
        self.project_id.position_budget_ids.unlink()

    def button_import(self):
        """ File management (unarchive if needed), database opening and call import router """
        if not self.import_file:
            raise exceptions.UserError(_('Please upload a file.'))
        
        db_models = ['Phases', 'ElevationGroups', 'a_elevations']
        filename, db_content, mimetype = self._uncompress(self.filename, self.import_file) # from `utilities.file.mixin`
        db_resource = self._open_external_database(filename, db_content, mimetype, self.encoding, db_models=db_models) # from `utilities.file.database`
        # dbsource is a record of `base.external.dbsource` (see module `server-env/base_external_dbsource`)
        
        self._run_import(db_resource)
        # self.with_context(import_budget_no_compute=True)._run_import(db_content, filename, mimetype)
        # self.with_context(import_budget_no_compute=False).project_id._budget_full_refresh()
        print(self.project_id.position_ids.read(['name']))
        print("import terminé")
        print('self.project_id', self.project_id)


    #===== Import logics =====#
    def _run_import(self, db_resource):
        """ Can be overriden to add import logic for other external database """

        if self.external_db_type == 'orgadata':
            self._run_orgadata_import(db_resource)

    def _get_interface(self, cols_external):
        """ Add any discovered cols of `cols_external` in active=False in
            `carpentry.position.budget.interface` and notify the users
            
            :arg cols_external:
                Cols of external database, which must corresponds
                 to `name` field of `carpentry.position.budget` records
            
            :return:
                Dict to pivot from external db col to `analytic_account_id`,
                 like: {col_name (str): analytic_account_id}
        """
        # Get known cols
        domain = [('external_db_type', '=', self.external_db_type)]
        Interface = self.env['carpentry.position.budget.interface'].with_context(active_test=False).sudo()
        interface_ids = Interface.search(domain)

        # Add new Orgadata cols if any
        cols_discovered = set(cols_external) - set(interface_ids.mapped('external_db_col'))
        vals_list = [{
            'external_db_col': col,
            'external_db_type': self.external_db_type,
        } for col in cols_discovered]
        if vals_list:
            Interface._create_default_and_ignore(vals_list)

        mapped_interface = {x.external_db_col: x.analytic_account_id.id for x in interface_ids.filtered('active')}
        return mapped_interface


    #===== Specific import logics =====#
    def _run_orgadata_import(self, db_resource):
        print('_run_orgadata_import', self, db_resource)
        read_result = self._read_orgadata(db_resource)
        self._write_orgadata(*read_result)
    
    def _read_orgadata(self, db_resource):
        # 1. Get `carpentry.group.lot`
        sql = "SELECT PhaseID, Name FROM Phases"
        cols_mapping = {'PhaseID': 'external_db_id', 'Name': 'name'}
        Phases = self._read_db(db_resource, sql, cols_mapping)
        
        # 2. Get `carpentry.position`
        # Orgadata has a M2M relation table `ElevationGroups` between lots and positions
        # Phases <-> Elevation x2x relation table
        sql = "SELECT ElevationGroupID, PhaseId FROM ElevationGroups"
        ElevationGroups_to_Phases = self._read_db(db_resource, sql, format_m2m=True)

        # ALY (2024-06-26) :
        # a. removed 'SystemName': 'range' which is in 'Elevations' but missing in 'a_elevations'
        # b. ElevationID and ElevationGroupId in 'Elevations' -> elevationId and elevationGroupId in 'a_elevations'
        sql = "SELECT elevationId, Name, Amount, Area, AutoDescription, elevationGroupId FROM a_elevations"
        cols_mapping = {
            'elevationId': 'external_db_id', 'Name': 'name',
            'Amount': 'quantity', 'Area': 'surface', 'AutoDescription': 'description'
        }
        Elevations = self._read_db(db_resource, sql, cols_mapping)

        # 3. Get `carpentry.position.budget`
        # cols of `a_elevations` are rows of carpentry Interface `carpentry.position.budget.interface`
        # don't pass any `cols_mapping`: one might discover new Orgadata columns
        Budgets = self._read_db(db_resource, "SELECT * FROM a_elevations")
        self._close_db(db_resource) # close connection with Orgadata mssql db

        return Phases, ElevationGroups_to_Phases, Elevations,Budgets

    def _write_orgadata(self, Phases, ElevationGroups_to_Phases, Elevations, Budgets):
        # 1. Get Odoo's budget column
        cols_orgadata = [x for x in Budgets[0]] if Budgets else []
        mapped_interface = self._get_interface(cols_orgadata)

        # 2. Write `carpentry.group.lot`
        domain = [('project_id', '=', self.project_id.id)]
        existing_lot_ids = self.env['carpentry.group.lot'].search(domain)
        lot_ids = self._import_data(Phases, existing_lot_ids)

        mapped_lot_ids = {x.external_db_id: x.id for x in lot_ids}
        # and resolve position-lot relation from Orgadata's M2M 'Elevation <> ElevationGroup <> Phases'
        for elevation in Elevations:
            phase_external_db_id_ = ElevationGroups_to_Phases.get(int(elevation.get('elevationGroupId')))
            elevation['lot_id'] = mapped_lot_ids.get(phase_external_db_id_)
            del elevation['elevationGroupId']
        
        # 3. Import carpentry.position
        existing_position_ids = self.env['carpentry.position'].search(domain)
        position_ids = self._import_data(Elevations, existing_position_ids)
        mapped_position_ids = {x.external_db_id: x.id for x in position_ids}
        
        # 4. Import carpentry.position.budget
        precision = self.env['decimal.precision'].precision_get('Product Price')
        # Sum-group budget of active columns, in the format for `carpentry_position_budget._erase_budget()`
        mapped_budget = defaultdict(float)
        for elevation in Budgets:
            position_id_ = mapped_position_ids.get(int(elevation.get('elevationId')))
            for col, analytic_account_id_ in mapped_interface.items():
                amount = elevation.get(col, 0.0)
                if not float_is_zero(float(amount), precision_digits=precision):
                    mapped_budget[(position_id_, analytic_account_id_)] += amount
        # Create if new, write/erase if existing, delete if not touched
        vals_list_budget = [
            {'position_id': key[0], 'analytic_account_id': key[1], 'amount': amount}
            for key, amount in mapped_budget.items()
        ]
        position_ids.position_budget_ids._erase_budget(vals_list_budget)
