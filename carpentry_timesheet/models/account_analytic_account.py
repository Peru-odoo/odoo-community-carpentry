# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountAnalyticAccount(models.Model):
    _inherit = ['account.analytic.account']

    budget_line_ids = fields.One2many(
        # for domain of `project_task.analytic_account_id`
        comodel_name='account.move.budget.line',
        inverse_name='analytic_account_id',
        string='Budget Lines'
    )
    timesheetable = fields.Boolean(
        string='Timesheetable?',
        compute='_compute_timesheetable',
        default=False,
        store=True,
        help='Can only be selected on Tasks if activated.'
             ' Depends on Product Template configuration.'
    )

    @api.depends(
        'product_tmpl_id',
        'product_tmpl_id.detailed_type',
        'product_tmpl_id.budget_ok',
        # 'product_tmpl_id.uom_id.category_id',
    )
    def _compute_timesheetable(self):
        # wtime = self.env.ref('uom.uom_categ_wtime')
        for analytic in self:
            analytic.timesheetable = (
                analytic.product_tmpl_id.id and
                analytic.product_tmpl_id.budget_ok and
                analytic.product_tmpl_id.detailed_type == 'service_office'
                # self.product_tmpl_id.uom_id.category_id.id == wtime.id
            )
    
    