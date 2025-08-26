# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command

class AnalyticMixin(models.AbstractModel):
    """ 
        Compute and store a `project_id` field from `analytic_distribution` (in priority),
        else from the parent object (`purchase.order` or `account.move`).

        Plus business logics to override analytic to INTERNAL project/budget
    """
    _inherit = ['analytic.mixin']

    #====== Fields methods ======#
    def _get_fields_project_id(self):
        """ Fields (in order) in which to lookup `project_id`
            Eg: order_id, picking_id, production_id, ...
        """
        return []

    #====== Fields ======#
    project_id = fields.Many2one(
        comodel_name='project.project',
        compute='_compute_project_id',
        store=True,
    )
    analytic_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        compute='_compute_analytic_ids',
        string='Analytic Accounts',
    )


    #====== Compute ======#
    @api.depends('analytic_distribution')
    def _compute_analytic_ids(self):
        """ Gather analytic account selected in the line's analytic distribution
            synthetic: only analytic_ids (no % distribution)
        """
        for record in self:
            distrib = record.analytic_distribution
            record.analytic_ids = distrib and [Command.set([int(x) for x in distrib.keys()])]

    def _compute_analytic_distribution_carpentry(self):
        """ Since `_compute_analytic_distribution` is re-defined on inheriting models,
            this method must be called *manually* from them to trigger mixin' logics
        """
        self._compute_project_id()
        self._enforce_internal_analytic()

    @api.depends(
        lambda self: ['analytic_distribution'] + [x + '.project_id' for x in self._get_fields_project_id()]
    )
    def _compute_project_id(self):
        """ 1. First cascade `project_id` of the parent record (if changed)
               to the line's analytic distribution 
            2. Then recompute `project_id`:
                a) from analytic first (if only 1 is set)
                b) else from parent's `project_id`
        """
        # Get all analytic accounts of projects
        data = self.env['project.project'].sudo().search_read(fields=['analytic_account_id'])
        mapped_projects_analytics = {x['analytic_account_id'][0]: x['id'] for x in data}
        parent_fields = self._get_fields_project_id()

        replace_dict_enforce = self._get_enforce_dict_analytic_internal()

        for record in self:
            projects_analytics = set()
            if record.analytic_distribution:
                projects_analytics = (
                    set(int(x) for x in record.analytic_distribution.keys())
                    & set(mapped_projects_analytics.keys())
                )

            new_id = record._get_project_from_parent(parent_fields)._origin.analytic_account_id.id
            if record._should_enforce_internal_analytic():
                new_id = replace_dict_enforce.get(new_id, new_id)

            args = (projects_analytics, new_id, mapped_projects_analytics)
            if record._origin.project_id != record.project_id:
                record._cascade_parent_project_to_analytic(*args)
            record._set_project_id_from_analytic_first(*args)

    def _cascade_parent_project_to_analytic(self, projects_analytics, new_id, mapped_projects_analytics):
        """ Update line's project analytic from parent """
        self.ensure_one()
        # deleted
        if not new_id and self.analytic_distribution and str(new_id) in self.analytic_distribution:
            self.analytic_distribution.pop(str(new_id))
        else:
            # added
            if new_id and not len(projects_analytics):
                self.analytic_distribution = (self.analytic_distribution or {}) | {new_id: 100}
            # replaced
            elif new_id:
                replace_dict = {x: new_id for x in mapped_projects_analytics.keys()}
                self.analytic_distribution = self._get_replaced_analytic(replace_dict)

    def _set_project_id_from_analytic_first(self, projects_analytics, new_id, mapped_projects_analytics):
        """ Sets `project_id` of line, from analytic (priority) or parent """
        self.ensure_one()
        if len(projects_analytics) == 1:
            analytic_id = next(iter(projects_analytics))
        else:
            analytic_id = new_id
        self.project_id = mapped_projects_analytics.get(analytic_id)

    #====== Helper methods ======#
    def _get_project_from_parent(self, parent_fields):
        """ Compute `project_id` from the fields listed in `_get_fields_project_id` """
        if self:
            self.ensure_one()
        
        for field in parent_fields:
            project_id = self[field].project_id
            if project_id:
                return project_id
        return self.env['project.project']
    
    def _get_replaced_analytic(self, replace_dict):
        new_dict = {}
        if self.analytic_distribution:
            for account_id, percent in self.analytic_distribution.items():
                new_account_id = replace_dict.get(int(account_id), int(account_id))
                new_dict[new_account_id] = new_dict.get(new_account_id, 0.0) + percent
        return new_dict


    #====== Internal analytics enforcment ======#
    def _enforce_internal_analytic(self):
        """ Forces analytic of *internal* project for all *storable* lines """
        if self._context.get('enforce_internal_analytic'):
            return
        self = (
            self.filtered(lambda record: record._should_enforce_internal_analytic())
            .with_context(enforce_internal_analytic=True)
        )
        if not self: # optim
            return

        replace_dict_enforce = self._get_enforce_dict_analytic_internal()
        for record in self:
            record.analytic_distribution = record._get_replaced_analytic(replace_dict_enforce)
    
    def _should_enforce_internal_analytic(self):
        return False
    
    def _get_enforce_dict_analytic_internal(self):
        """ [For inheritance] Returns `replace_dict` to be applied in `_enforce_internal_analytic`
            Rule: replace any projects by *INTERNAL project*
        """
        sr_result = self.env['project.project'].sudo().search_read(fields=['analytic_account_id'])
        internal_id = self.company_id.internal_project_id.analytic_account_id.id
        return {x: internal_id for x in [x['analytic_account_id'][0] for x in sr_result]}
