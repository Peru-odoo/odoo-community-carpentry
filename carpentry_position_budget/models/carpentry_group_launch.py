# -*- coding: utf-8 -*-

from odoo import api, models, fields, exceptions, _

class CarpentryGroupLaunch(models.Model):
    _name = 'carpentry.group.launch'
    _inherit = ['carpentry.group.launch', 'carpentry.group.budget.mixin']

    budget_ids = fields.One2many(
        comodel_name='carpentry.budget.available',
        inverse_name='launch_id',
        string='Budgets',
        readonly=True,
    )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_budget_reservation(self):
        """ Prevent unlink launch is used in PO, MO, Picking, ... """
        domain = self._get_domain_affect('record')
        affectations = self.env['carpentry.group.affectation'].search(domain)
        launch_ids_affected = affectations.mapped('record_id')
        if any([launch.id in launch_ids_affected for launch in self]):
            raise exceptions.UserError(_(
                'This launch is already used in a budget reservation like a Purchase Order, '
                ' Manufacturing Order or Picking.'
            ))
        