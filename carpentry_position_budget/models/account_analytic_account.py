# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountAnalyticAccount(models.Model):
    _inherit = ['account.analytic.account']

    budget_type = fields.Selection(
        selection_add=[
            ('production', 'Production'),
            ('installation', 'Installation'),
            ('project_global_cost', 'Project global costs'),
        ],
        ondelete={
            'production': 'set service',
            'installation': 'set service',
            'project_global_cost': 'set goods',
        }
    )
    template_line_ids = fields.One2many(
        # for domain in Interface
        comodel_name='account.move.budget.line.template',
        inverse_name='analytic_account_id'
    )


    def _get_default_line_type(self):
        if self.budget_type in ['service', 'production', 'installation']:
            return 'workforce'
        return super()._get_default_line_type()


    #==== Affectation matrix =====#
    def _get_quantities_available(self, affectations):
        """ Available budget on budget matrix depends on:
            - the Launch (affectation.record_ref) *and*
            - the Budget type (affectation.group_ref) *and*
            - the PO or MO (affectation.section_ref)
        """
        section = fields.first(affectations).section_ref
        launch_ids = affectations.mapped('record_id')
        analytic_ids = affectations.mapped('group_id')
        return (
            self.env['carpentry.group.launch'].sudo().browse(launch_ids).
            _get_remaining_budget(section, analytic_ids)
        )
