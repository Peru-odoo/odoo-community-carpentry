# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
import base64, io, openpyxl, os

EXTERNAL_DB_TYPE = [
    ('orgadata', 'Orgadata')
]
SEPARATOR_COLOR = '-RAL' # example: "174170-RAL7016 Sat 30"

class CarpentryMrpImportWizard(models.TransientModel):
    _name = "carpentry.mrp.import.wizard"
    _description = "Carpentry MRP Import Wizard"
    _inherit = ['utilities.file.mixin', 'utilities.database.mixin']

    REPORT_FILENAME = 'report/report_mrp_component_unknown.xlsx'

    #===== Fields =====#
    mode = fields.Selection(
        selection=[
            ('component', 'Components'),
            ('final_product', 'Final products'),
        ],
        required=True,
        string='Import mode'
    )
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

    # imported data
    product_ids = fields.One2many(comodel_name='product.product', store=False)
    supplierinfo_ids = fields.One2many(comodel_name='product.supplierinfo', store=False)

    # report
    move_raw_ids = fields.One2many(related='production_id.move_raw_ids')
    substituted_product_ids = fields.One2many(comodel_name='product.product', store=False)
    ignored_product_ids = fields.One2many(comodel_name='product.product', store=False)

    #===== Buttons =====#
    def button_truncate(self):
        self.production_id.move_raw_ids.unlink()
    
    def button_import(self):
        if not self.import_file:
            raise exceptions.UserError(_('Please upload a file.'))
        
        if self.mode == 'component':
            self._action_import_component()
        elif self.mode == 'final_product':
            self._action_import_final_product()

    def _action_import_final_product(self):
        """ Final products: excel file to import Odoo records in the MO """
        pass

    def _action_import_component(self):
        """ Components: file is Orgadata database """
        filename, db_content, mimetype = self._uncompress(self.filename, self.import_file) # from `utilities.file.mixin`
        db_models = ['AllArticles', 'Elevations']
        db_resource = self._open_external_database(filename, db_content, mimetype, self.encoding, db_models=db_models) # from `utilities.file.database`
        self._run_import(db_resource)

        self.state = 'done'
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'context': self._context,
            'view_mode': 'form',
            'target': 'new',
        }


    #===== Import logics =====#
    def _run_import(self, db_resource):
        components, final_products = self._read_external_db(db_resource)
        self._close_db(db_resource) # close connection with external db

        # Get products
        mapped_components = {x['default_code']: x for x in components}
        Product = self.env['product.product'].with_context(active_test=False)
        products = Product.search([('default_code', 'in', list(mapped_components.keys()))])
        self.product_ids = products

        # Unknown products
        default_code_list = products.mapped('default_code')
        unknown = [v for k, v in mapped_components.items() if k not in default_code_list]

        # Import logic : substitute -> import -> make report (consumable & unknown)
        self._substitute()
        self._ignore()
        self._import_components(mapped_components)

        # Report & message
        consu = [
            mapped_components.get(x.product_id.default_code)
            for x in self.move_raw_ids.filtered(lambda x: x.product_id.type == 'consu')
        ]
        report_binary = self._make_report(mapped_components, final_products, unknown, consu)
        self._submit_chatter_message(unknown, consu, report_binary)

    def _read_external_db(self, db_resource):
        """ Can be overriden to add import logic for other external database """

        if self.external_db_type == 'orgadata':
            # Components
            # if `ColorInfoInternal` is given, suffix it to the `default_code`
            fields = f"""
                IIF(
                    ColorInfoInternal IS NOT NULL,
                    ArticleCode_OrderCode || '{SEPARATOR_COLOR}' || ColorInfoInternal,
                    ArticleCode_OrderCode
                ) AS default_code,
                Units_Output AS product_uom_qty,
                Units_Unit AS uom_name,
                Description AS name,
                PriceGross AS price,
                Discount AS discount
            """
            sql = f"""
                SELECT {fields} FROM AllArticles
                UNION
                SELECT {fields} FROM AllProfiles
            """
            components = self._read_db(db_resource, sql)

            # Final products (positions)
            sql = f"""
                SELECT
                    Name AS description_picking,
                    Amount AS product_uom_qty
                FROM Elevations
            """
            final_products = self._read_db(db_resource, sql)

        return components, final_products
    
    def _substitute(self):
        substituted = self.product_ids.filtered('product_substitution_id')
        if substituted:
            self.product_ids += substituted.product_substitution_id - substituted
            self.substituted_product_ids = substituted

    def _ignore(self):
        active = self.product_ids.filtered('active')
        self.ignored_product_ids = self.product_ids - active
        self.product_ids = active

    def _import_components(self, mapped_components):
        """ Update products prices (first)
            and add product materials as MO's components
        """
        supplierinfo_vals_list, component_vals_list = [], []
        for product in self.product_ids:
            data = mapped_components.get(product.default_code)
            if not data:
                continue
        
            # Update product price
            supplierinfo_vals_list.append({
                'product_id': product.id,
                'partner_id': product.preferred_supplier_id.id,
                'price': data.get('price'),
                'discount': data.get('discount'),
            })

            # Create need (reservation)
            component_vals_list.append(Command.create(
                self.production_id._get_move_raw_values(
                    product,
                    data.get('product_uom_qty'),
                    product.uom_id,
                ))
            )
        self.supplierinfo_ids = self.env['product.supplierinfo'].sudo().create(supplierinfo_vals_list)
        self.production_id.move_raw_ids = component_vals_list

    def _make_report(self, mapped_components, final_products, unknown, consu):
        def __write_section(start_row, title, cols, vals_list):
            # Title
            cell = 'A' + str(start_row)
            sheet[cell] = title
            sheet[cell].font = Font(size=14, bold=True)
            
            # Headers
            line = str(start_row+1)
            for i, header in enumerate(cols, start=1):
                cell = 'A' + str(start_row+1)
                sheet[cell] = header
                sheet[cell].font = openpyxl.styles.Font(bold=True)
                sheet[cell].fill = openpyxl.styles.PatternFill("solid", fgColor="B4C7DC")
            
            # Content
            row_cursor = start_row+2 # title + header
            for row, vals in enumerate(vals_list, start=row_cursor):
                for col, key in enumerate(list(cols.values()), start=1):
                    sheet.cell(row=row, column=col).value = vals[key]
                    # sheet.insert_rows(row+1)
            
            return row_cursor + 2 # empty lines separation

        # Load the Excel template
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../' + self.REPORT_FILENAME)
        workbook = openpyxl.load_workbook(path)
        sheet = workbook.active

        # Titles & translations
        titles = {
            'A1': _('Report for the import of manufacturing Components'),
            'A2': _('Project'),
            'A3': _('Manufacturing Order'),
            'A4': _('Date'),
            'B2': self.production_id.project_id.display_name,
            'B3': self.production_id.display_name,
            'B4': fields.Date.context_today(self),
        }
        for cell, text in titles.items():
            sheet[cell] = text
            sheet[cell].font = openpyxl.styles.Font(size=14, bold=True)

        # Final products
        row_cursor = 6
        cols = {
            _('Description'): 'description_picking',
            _('Quantity'): 'product_uom_qty',
        }
        row_cursor = __write_section(row_cursor, _('Final products'), cols, final_products)

        # Components
        sections = {
            _('Unknown'): unknown.values(),
            _('Consumable'): consu.values(),
            _('Imported components'): [mapped_components.get(x.default_code) for x in self.product_ids],
            _('Substituted components'): [mapped_components.get(x.default_code) for x in self.substituted_product_ids],
            _('Ignored components'): [mapped_components.get(x.default_code) for x in self.ignored_product_ids]
        }
        cols = {
            _('Reference'): 'default_code',
            _('Name'): 'name',
            _('Quantity'): 'product_uom_qty',
            _('Unit of Measure'): 'uom_name',
            _('Unit Price'): 'price',
        }
        for section, vals_list in sections:
            row_cursor = __write_section(row_cursor, section, cols, vals_list)

        # Save the file to a BytesIO stream
        output_stream = io.BytesIO()
        workbook.save(output_stream)
        # workbook.close()
        print('output_stream', output_stream)

        output_stream.seek(0)
        return output_stream.read() # binary, NOT base64 encoded for `message_post`

    def _submit_chatter_message(self, unknown, consu, report_binary):
        mail_values = {
            'message_type': 'notification',
            'subtype_xmlid': 'mail.mt_note',
            'is_internal': True,
            'partner_ids': [],
            'body': _(f"""
                Component import:
                <ul>
                    <li><strong>{len(self.product_ids)}</strong> components added</li>
                    <li><strong>{len(consu)}</strong> consumable maybe to order separatly</li>
                    <li><strong>{len(self.substituted_product_ids)}</strong> substituted references</li>
                    <li><strong>{len(self.ignored_product_ids)}</strong> explicitely ignored</li>
                    <li><strong>{len(unknown)}</strong> unknown products</li>
                </ul>
            """),
            'attachments': [] if not report_binary else [
                (_('Component report'), report_binary)
            ]
        }
        
        self.production_id.message_post(**mail_values)
