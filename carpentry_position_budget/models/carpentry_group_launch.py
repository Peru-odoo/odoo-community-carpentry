# -*- coding: utf-8 -*-

from odoo import api, models, fields, exceptions, _
from odoo.osv import expression

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
            action = (
                self.env['ir.actions.act_window']
                ._for_xml_id('carpentry_position_budget.action_open_budget_report_remaining')
            ) | {
                'name': _("Budget reservations of %s", ', '.join(self.mapped('display_name'))),
                'view_mode': 'tree',
                'domain': expression.AND([
                    self._get_domain_affect(),
                    [('budget_type', '!=', None)],
                ]),
            }

            raise exceptions.RedirectWarning(
                message=_(
                    'This launch is already used in a budget reservation like a Purchase Order, '
                    ' Manufacturing Order or Picking.'
                ),
                action=action,
                button_text=_("Show reservations")
            )
