# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ManufacturingOrder(models.Model):
    _inherit = ['mrp.workorder']

    costs_hour_account_id = fields.Many2one(
        related='workcenter_id.costs_hour_account_id',
    )

    #===== Budget & affectation =====#
    @api.depends('time_ids.date_end')
    def _compute_date_budget(self):
        """ Date of expense, gain/loss = last time """
        rg_result = self.env['mrp.workcenter.productivity'].read_group(
            domain=[('workorder_id', 'in', self.ids)],
            groupby=['workorder_id'],
            fields=['date_end:max'],
        )
        mapped_data = {x['workorder_id'][0]: x['date_end'] for x in rg_result}
        for workorder in self:
            workorder.date_budget = mapped_data.get(workorder.id)
        return super()._compute_date_budget()
