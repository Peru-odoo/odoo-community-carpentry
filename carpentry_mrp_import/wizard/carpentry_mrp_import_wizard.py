# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
import base64, io, openpyxl, os

EXTERNAL_DB_TYPE = [
    ('orgadata', 'Orgadata')
]

class CarpentryMrpImportWizard(models.TransientModel):
    _name = "carpentry.mrp.import.wizard"
    _description = "Carpentry MRP Import Wizard"
    _inherit = ['utilities.file.mixin', 'utilities.database.mixin']

    REPORT_FILENAME = 'report/report_mrp_component_unknown.xlsx'

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
    unknown_product_xlsx = fields.Binary(string='Unkown products', readonly=True)
    unknown_product_filename = fields.Char(compute='_compute_unknown_product_filename')
    # other
    supplierinfo_ids = fields.One2many(comodel_name='product.supplierinfo', store=False)
    purchaseorder_ids = fields.One2many(comodel_name='purchase.order', store=False)


    #===== Compute =====#
    def _compute_unknown_product_filename(self):
        for wizard in self:
            wizard.unknown_product_filename = _('Ignored components report') + '.xlsx'

    #===== Buttons =====#
    def button_truncate(self):
        self.production_id.move_raw_ids.unlink()
    
    def button_import(self):
        if not self.import_file:
            raise exceptions.UserError(_('Please upload a file.'))
        
        filename, db_content, mimetype = self._uncompress(self.filename, self.import_file) # from `utilities.file.mixin`
        db_models = ['AllArticles']
        db_resource = self._open_external_database(filename, db_content, mimetype, self.encoding, db_models=db_models) # from `utilities.file.database`
        self._run_import(db_resource)

        self.state = 'done'
        fields = ['imported_product_ids', 'substituted_product_ids', 'ignored_product_ids', 'non_stored_product_ids', 'supplierinfo_ids', 'purchaseorder_ids']
        context = {'default_' + x: [Command.set(self[x].ids)] for x in fields}
        print('context', context)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'context': context,
            'view_mode': 'form',
            'target': 'new',
        }


    #===== Import logics =====#
    def _run_import(self, db_resource):
        vals_list = self._read_external_db(db_resource)

        # Get products
        mapped_products = {x['default_code']: x for x in vals_list}
        Product = self.env['product.product'].with_context(active_test=False)
        products = Product.search([('default_code', 'in', list(mapped_products.keys()))])

        # Unknown products -> XLSX
        self._set_unknown_products_xlsx(products, mapped_products)
        
        # Filter & import
        self._filter_products(products)
        self._update_supplierinfo(mapped_products)
        self._import_components(mapped_products)
        self._import_non_stored(mapped_products)

    # ---- Read & filter ----
    def _read_external_db(self, db_resource):
        """ Can be overriden to add import logic for other external database """

        if self.external_db_type == 'orgadata':
            sql = """
                SELECT
                    ArticleCode_OrderCode AS default_code,
                    Units_Output AS product_uom_qty,
                    Units_Unit AS uom_name,
                    Description AS name,
                    PriceGross AS price,
                    Discount AS discount
                FROM
                    AllArticles
                """
            vals_list = self._read_db(db_resource, sql)
            self._close_db(db_resource) # close connection with external db
            return vals_list
    
    def _filter_products(self, products):
        # 1. Substitute
        substituted = products.filtered('product_substitution_id')
        if substituted:
            self.substituted_product_ids = substituted
            products += products.product_substitution_id - substituted

        # 2. Ignore
        self.ignored_product_ids = products.filtered(lambda x: not x.active or not x.purchase_ok)
        products -= self.ignored_product_ids

        # 3. Storable => reservation
        self.imported_product_ids = products.filtered(lambda x: x.type == 'product')
        
        # 4. Non-storable => order
        self.non_stored_product_ids = products - self.imported_product_ids


    # ---- Write ----
    def _update_supplierinfo(self, mapped_products):
        vals_list = []
        for product in self.imported_product_ids:
            vals = mapped_products.get(product.default_code)
            vals_list.append({
                'product_id': product.id,
                'supplier_id': product.preferred_supplier_id.id,
                'price': vals.get('price'),
                'discount': vals.get('discount'),
            })
        
    def _import_components(self, mapped_products):
        """ Update products prices (first)
            and add product materials as MO's components
        """
        supplierinfo_vals_list, component_vals_list = [], []
        for product in self.imported_product_ids:
            data = mapped_products.get(product.default_code)
            supplierinfo_vals_list.append({
                'product_id': product.id,
                'partner_id': product.preferred_supplier_id.id,
                'price': data.get('price'),
                'discount': data.get('discount'),
            })
            component_vals_list.append(Command.create(
                self.production_id._get_move_raw_values(
                    product,
                    data.get('product_uom_qty'),
                    product.uom_id,
                ))
            )
        self.env['product.supplierinfo'].sudo().create(supplierinfo_vals_list)
        self.production_id.move_raw_ids = component_vals_list

    def _import_non_stored(self, mapped_products):
        # >>>> regarder si:
        # - ajouter à stock.warehouse.orderpoint (tricher: normalement que pour les storable)
        # - ré-utiliser les logiques/méthodes de stock.warehouse.orderpoint (en raccourci)
        pass

    def _set_unknown_products_xlsx(self, products, mapped_products):
        found = products.mapped('default_code')
        unknown = [v for k,v in mapped_products.items() if k not in found]

        # Load the provided Excel template
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../' + self.REPORT_FILENAME)
        workbook = openpyxl.load_workbook(path)
        sheet = workbook.active

        # Write custom name to cell B2
        sheet["B2"] = self.production_id.display_name

        # Fill the sheet with data starting from row 5
        start_row = 5
        cols = ['default_code', 'product_uom_qty', 'uom_name', 'name', 'price']
        for row, vals in enumerate(mapped_products.values(), start=start_row):
            for col, key in enumerate(cols, start=1):
                sheet.cell(row=row, column=col).value = vals.get(key)

        # Save the file to a BytesIO stream
        output_stream = io.BytesIO()
        workbook.save(output_stream)
        workbook.close()

        # Convert to Base64
        output_stream.seek(0)
        self.unknown_product_xlsx = base64.b64encode(output_stream.read()).decode('utf-8')
