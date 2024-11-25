# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command, exceptions, _

class PositionMerge(models.TransientModel):
    _name = "carpentry.position.merge.wizard"
    _description = "Position merge wizard"

    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    position_id_target = fields.Many2one('carpentry.position', string='Position to keep', required=True,
        domain="[('id', 'in', position_ids_to_merge)]")
    position_ids_to_merge = fields.Many2many('carpentry.position', string='Duplicates to merge in "target"', required=True,
        domain="[('project_id', '=', project_id)]")

    @api.model
    def default_get(self, field_names):
        defaults_dict = super().default_get(field_names)
        position_ids = self.env['carpentry.position'].browse(self._context.get('active_ids', []))
        if len(position_ids.ids) == 1: # if 1, user must have clicked on button in tree's row => let's pre-fill duplicate list
            defaults_dict['position_id_target'] = position_ids
            position_ids = self.env['carpentry.position'].search([('project_id', '=', position_ids.project_id.id), ('name', '=', position_ids.name)])
        defaults_dict.update({'position_ids_to_merge': [Command.set([x.id for x in position_ids])], 'project_id': position_ids.project_id.id})
        return defaults_dict
    
    def button_merge(self):
        # user exceptions
        position_ids_to_merge = self.position_ids_to_merge - self.position_id_target
        if not position_ids_to_merge.ids: # may happen if user only put in 'position_ids_to_merge' the 'position_id_target'
            raise exceptions.UserError(_('No duplicates to merge.'))
        if sum(self.position_ids_to_merge.affectation_ids.mapped('quantity_affected')) > 0:
            raise exceptions.UserError(_('Ensure duplicates have no phases and launches affectations before merging budgets.'))

        # to respect 'carpentry.position.budget' unique index, let's *add-or-update* budgets instead instead of updating their 'position_id'
        rg_result = self.env['carpentry.position.budget'].read_group([('position_id', 'in', position_ids_to_merge.ids)],
            fields=['product_id', 'amount:sum'], groupby=['product_id'])
        budgets_to_add = dict([(x['product_id'][0], x['amount']) for x in rg_result])
        product_ids_existing = self.position_id_target.budget_ids.product_id.ids
        for product_id, amount_to_add in budgets_to_add.items():
            if product_id in product_ids_existing:
                self.position_id_target.budget_ids.filtered(lambda x: x.product_id.id == product_id).amount += amount_to_add
            else:
                self.position_id_target.budget_ids = [Command.create({'amount': amount_to_add})]
        # delete duplicates and go back to refreshed position view
        position_ids_to_merge.unlink()

