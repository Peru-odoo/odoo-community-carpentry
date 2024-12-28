# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

EXTERNAL_DB_TYPE = [
    ('orgadata', 'Orgadata')
]

class CarpentryMrpImportWizard(models.TransientModel):
    _name = "carpentry.mrp.import.import"
    _description = "Carpentry MRP Import Wizard"
    _inherit = ['utilities.file.mixin', 'utilities.database.mixin']

    #===== Fields =====#
    state = fields.Selection(
        selection=[
            ('draft', 'Import'),
            ('done', 'Done'),
        ],
        string='State',
        default='draft'
    )
    production_id = fields.Many2one(
        comodel_name='mrp.production',
        string='Manufacturing Order',
        required=True,
        readonly=True,
    )
    import_file = fields.Binary(
        string='External DB file'
    )
    filename = fields.Char(
        string='Filename'
    )

    external_db_type = fields.Selection(
        selection=EXTERNAL_DB_TYPE,
        string='Type of external database',
        default=EXTERNAL_DB_TYPE[0][0],
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

    # -- imported data --
    # products
    imported_product_ids = fields.One2many(comodel_name='product.product', store=False)
    substituted_product_ids = fields.One2many(comodel_name='product.product', store=False)
    ignored_product_ids = fields.One2many(comodel_name='product.product', store=False)
    non_stored_product_ids = fields.One2many(comodel_name='product.product', store=False)
    # unknown products
    unknown_product_xlsx = fields.Binary(
        string='Unkown products'
    )
    # other
    supplierinfo_ids = fields.One2many(comodel_name='product.supplierinfo', store=False)
    purchaseorder_ids = fields.One2many(comodel_name='purchase.order', store=False)

    #===== Button =====#
    def button_truncate(self):
        self.production_id.move_raw_ids.unlink()
    
    def button_import(self):
        """ File management (unarchive if needed), database opening and call import router """
        if not self.import_file:
            raise exceptions.UserError(_('Please upload a file.'))
        
        filename, db_content, mimetype = self._uncompress(self.filename, self.import_file) # from `utilities.file.mixin`
        
        db_models = ['AllArticles']
        db_resource = self._open_external_database(filename, db_content, mimetype, self.encoding, db_models=db_models) # from `utilities.file.database`
        # dbsource is a record of `base.external.dbsource` (see module `server-env/base_external_dbsource`)
        
        self._run_import(db_resource)


    #===== Import logics =====#
    def _run_import(self, db_resource):
        """ Can be overriden to add import logic for other external database """

        if self.external_db_type == 'orgadata':
            self._run_orgadata_import(db_resource)

    def _import_components(self):
        pass
        # supplierinfo first
        # for product in self.imported_product_ids:
            # _get_move_raw_values(self, product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False):

    def _import_non_stored(self):
        # >>>> regarder si:
        # - ajouter à stock.warehouse.orderpoint (tricher: normalement que pour les storable)
        # - ré-utiliser les logiques/méthodes de stock.warehouse.orderpoint (en raccourci)
        pass

    def _build_unknown_products_xlsx(self, products, mapped_product):
        found = products.mapped('default_code')
        unknown = [x for x in mapped_product if x['default_code'] not in found]

        # self.unknown_product_xlsx = 'base64...'
    

    def _write_products(self, vals_list):
        # Get products
        mapped_products = {x['default_code']: x for x in vals_list}
        Product = self.env['product.product'].with_context(active_test=False)
        products = Product.search([('default_code', 'in', mapped_products.keys())])

        # Unknown -> XLSX
        self._build_unknown_products_xlsx(products, mapped_product)
        
        # Filter & import
        self._filter_products(products)
        self._import_components()
        self._import_non_stored()

        self.state = 'done'

    def _filter_products(self, products):
        # 1. Substitute
        self.substituted_product_ids = products.filtered('product_substitution_id')
        products += products.product_substitution_id - substituted

        # 2. Ignore
        self.ignored_product_ids = products.filtered(lambda x: x.active and x.purchase_ok)
        products -= self.ignored_product_ids

        # 3. Storable => reservation
        self.imported_product_ids = products.filtered(lambda x: x.type == 'product')
        
        # 4. Non-storable => order
        self.non_stored_product_ids = products - self.imported_product_ids




    #===== Specific import logics =====#
    def _run_orgadata_import(self, db_resource):
        read_result = self._read_orgadata(db_resource)
        self._write_orgadata(*read_result)
    
    def _read_orgadata(self, db_resource):
        # 1. Get `carpentry.group.lot`
        sql = """
            SELECT
                ArticleCode_OrderCode AS default_code,
                Units_Output AS product_uom_qty,
                Description AS name,
                PriceGross AS price,
                Discount AS discount
            FROM
                AllArticles
            """
        vals_list = self._read_db(db_resource, sql)
        self._close_db(db_resource) # close connection with external db
        return vals_list

    def _write_orgadata(self, vals_list):
        self._write_products(vals_list)
    