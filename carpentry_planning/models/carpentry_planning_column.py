# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command, exceptions
from collections import defaultdict

class CarpentryPlanningColumn(models.Model):
    _name = "carpentry.planning.column"
    _description = "Carpentry Planning Column"
    _order = 'sequence'
    _log_access = False

    #===== Fields' methods =====#
    def _selection_identifier_res_model(self):
        model_ids = self.env['ir.model'].sudo().search([])
        return [(model.model, model.name) for model in model_ids]

    #===== Fields =====#
    # core
    name = fields.Char(
        string='Name',
        translate=True
    )
    res_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Card Model'
        # can't set `required=True` for `comodel_name='ir.model'`
    )
    res_model_shortname = fields.Char(
        compute='_compute_res_model_shortname'
    )
    sequence = fields.Integer(
        default=1
    )
    sticky = fields.Boolean(
        default=False,
        help='If the card is displayed whatever domain filter on Planning view (e.g. Needs Categories).'
    )

    # Identifier value to route/discrepencies records of same model towards 2 or more columns
    identifier_ref = fields.Reference(
        # for user-input (only) in tree view
        selection='_selection_identifier_res_model',
        compute='_compute_identifier_ref',
        inverse='_inverse_identifier_ref',
        help='Identifier value is needed when 2 columns get their source from same Model.'
             ' The identifier model must have a `column_id` field holding the routing logic.'
             ' Example: Task Needs to route towards `Needs (Method)` or `Needs (Field)`',
        precompute=True # for constrain `_constrain_identifier_required()`
    )
    identifier_res_id = fields.Many2oneReference(
        model_field='identifier_res_model',
        string='Identifier ID',
    )
    identifier_res_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Identifier Model ID',
        ondelete='cascade'
    )
    identifier_res_model = fields.Char(
        string='Identifier Model',
        related='identifier_res_model_id.model',
    )
    identifier_required = fields.Boolean(
        # UI field
        compute='_compute_identifier_required'
    )

    # display
    fold = fields.Boolean(
        string='Folded?',
        default=False,
        help='Whether the column is hidden in the planning (for all users).'
    )
    icon = fields.Char(
        string='Icon',
        help='fa fa-xxxx'
    )
    can_open = fields.Boolean(
        default=True,
        string='Kanban Card is clickable'
    )

    #===== Constrains =====#
    _sql_constraints = [(
        "uniq_column",
        "UNIQUE (res_model_id, identifier_res_model_id, identifier_res_id)",
        "This identifier is already used in another column."
    )]

    @api.constrains('res_model_id', 'identifier_res_id')
    def _constrain_identifier_required(self):
        """ Especially needed for such scenario:
            1. Create a 1st column without identifier
            2. Create a 2nd column on same model
            => (!) 1st column is missing its identifier
        """
        all_column_ids = self._compute_identifier_required()
        for column in all_column_ids:
            if column.identifier_required and not column.identifier_res_id:
                raise exceptions.ValidationError(
                    _("Column %s requires an Identifier", column.name)
                )

    #===== CRUD =====#
    def _rebuild_sql_view(self):
        self.env['carpentry.planning.card'].sudo()._rebuild_sql_view()
    
    def _synch_mirroring_column_id(self):
        """ Update in `identifier_res_model` model mirroring `column_id` field """
        if self._context.get('no_test_mirroring_column_id'):
            return
        
        for column_id in self.filtered(lambda x: x.identifier_ref):
            try:
                column_id.identifier_ref._synch_mirroring_column_id(column_id)
            except:
                raise exceptions.ValidationError(_(
                    "Model of identifier %s cannot be chosen (not foreseen for it)."
                    " Column: %s", column_id.identifier_ref, column_id.name
                ))
    
    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        result._synch_mirroring_column_id()
        # /!\ Cannot rebuild SQL view on `create()`:
        # when the other module are being installed, `create()` is called while their models
        # is not in registry => this fails SQL view to rebuild (models or fields missing in database)
        # self._rebuild_sql_view()
        return result
    
    def unlink(self):
        result = super().unlink()
        self._rebuild_sql_view()
        return result
    
    def write(self, vals):
        result = super().write(vals)

        # Rebuild SQL View
        fields_to_update = ['sequence', 'res_model_id', 'fold']
        if any([field in vals for field in fields_to_update]):
            self._rebuild_sql_view()
        
        # Mirroring `column_id`
        if 'identifier_res_id' in vals:
            self._synch_mirroring_column_id()

        return result
    
    
    #===== Compute =====#
    def _compute_res_model_shortname(self):
        for column in self:
            column.res_model_shortname = column.res_model_id.model.replace('carpentry.', '').replace('.', '_')

    @api.depends('identifier_res_model_id', 'identifier_res_id')
    def _compute_identifier_ref(self):
        for column in self:
            if column.identifier_res_model_id.id and column.identifier_res_id:
                column.identifier_ref = '%s,%s' % (column.identifier_res_model, column.identifier_res_id)
            else:
                column.identifier_ref = False
    
    def _inverse_identifier_ref(self):
        model_ids = self.env['ir.model'].sudo().search([])
        mapped_model_ids = {x.model: x.id for x in model_ids}
        for column in self:
            identifier = column.identifier_ref
            column.identifier_res_id = bool(identifier) and identifier.id
            column.identifier_res_model_id = bool(identifier) and mapped_model_ids.get(identifier._name)

    @api.depends('res_model_id')
    def _compute_identifier_required(self):
        """ If there is at least 1 other column with same model:
            `identifier_ref` is `required` in view
        """
        # Get count of models occurence in the planning's column
        all_column_ids = self.sudo().with_context(active_test=False).search([])
        mapped_count = defaultdict(int)
        for column in all_column_ids:
            mapped_count[column.res_model_id.id] += 1
        
        # Take care of ongoing user changes
        for column in self.filtered(lambda x: '_origin' in x):
            mapped_count[column.res_model_id.id] += 1
            mapped_count[column._origin_.res_model_id.id] -= 1
        
        for column in all_column_ids:
            column.identifier_required = mapped_count.get(column.res_model_id.id, 0) > 1
        
        return all_column_ids # quick optim, see coresponding constrain

    #===== RPC calls (columns' sub-headers) =====#
    def get_headers_data(self, launch_id_):
        """ Return data like icon, milestone and budgets that appears
            in place of kanban's <progressbar />
        """
        launch_id = self.env['carpentry.group.launch'].browse(launch_id_)

        # milestones data preformatting
        mapped_milestone_data = defaultdict(list)
        for data in launch_id.milestone_ids.read(['id', 'name', 'icon', 'date', 'column_id']):
            column_id = data['column_id'][0]; del(data['column_id'])
            data['week'] = bool(data['date']) and data['date'].isocalendar()[1]
            mapped_milestone_data[column_id].append(data)
        
        
        # json return
        return {
            column.id: {
                'icon': column.icon,
                'milestones': mapped_milestone_data.get(column.id, []),
                'budgets': []
            } | (
                # specific custom other headers data per columns
                self.env[column.res_model_id.model]._get_planning_subheaders(self, launch_id)
                if '_get_planning_subheaders' in self.env[column.res_model_id.model] else {}
            )
            for column in self
        }
