# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.osv import expression

class CarpentryPositionBudgetInterface(models.Model):
    """ This model is a translation table from columns of an external DB model to the `carpentry.position.budget` table.
        Lines sequences are also important to shape the order of a project's budget in `account.move.budget`
    """
    _name = 'carpentry.position.budget.interface'
    _description = 'Interface for Position Budget'
    _order = 'sequence'
    _rec_name = 'external_db_col'
    
    #===== Fields' methods =====#
    def _selection_external_db_type(self):
        return [
            ('orgadata', _('Orgadata'))
        ]
    
    #===== Fields =====#
    # external DB
    external_db_col = fields.Char(
        string='External column name',
        required=False
    )
    external_db_type = fields.Selection(
        # foresee possible extension, for other software data model
        selection=_selection_external_db_type,
        string='Type of external database',
        default=lambda self: self._selection_external_db_type()[0][0],
        required=True
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
        index='btree_not_null',
        ondelete='restrict',
        domain=[('product_tmpl_id', '!=', False)],
        help='Make the link between budget, income and charges. Must have a "Default Product"'
            ' in order to distinguish budget types (service or consummable).'
    )
    detailed_type = fields.Selection(
        # identifies goods (€) vs. services (h)
        related='analytic_account_id.product_tmpl_id.detailed_type',
        help='Identifies the type of budget amount from remote database,'
             ' i.e. work-force quantities or currency amount. Corresponds to'
             ' the type of the default product on analytic account\'s.',
        required=True
    )

    active = fields.Boolean(
        string='To use?',
        default=True,
        help='If archived, any budget from external source of this column will be ignored at during import.'
    )
    sequence = fields.Integer()

    #===== Constraints =====#
    _sql_constraints = [(
        "unique_col",
        "UNIQUE (external_db_col, external_db_type)",
        "This 'External column' already exists for this type of external database."
    )]

    #===== Business logics =====#
    def _create_default_and_ignore(self, vals_list):
        """ Called programmatically from import wizard, when needed to add an unactive line and inform the user """
        for vals in vals_list:
            vals['active'] = False

            # Inform the user
            self.env.user.notify_info(_(
                'Column %s was added to the import interface with External Database as ignored by default.',
                vals['external_db_col']
            ))
        return super().create(vals_list)
