# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
import base64
from collections import defaultdict

class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['purchase.order', 'project.default.mixin']
    _rec_name = 'display_name'

    #====== Fields ======#
    project_id = fields.Many2one(
        # required on the view. Must not be in ORM because of replenishment (stock.warehouse.orderpoint)
        required=False
    )
    description = fields.Char(
        string='Description'
    )
    launch_ids = fields.Many2many(
        comodel_name='carpentry.group.launch',
        relation='purchase_order_launch_rel',
        string='Launches',
        domain="[('project_id', '=', project_id)]",
    )
    task_ids = fields.One2many(
        related='launch_ids.task_ids'
    )
    
    #===== Constrain =====#
    @api.constrains('project_id', 'launch_ids')
    def _constrain_launch_ids(self):
        """ Launch_ids must belong to the project
            (a discrepency could happen since `project_id` is writable)
        """
        for purchase in self:
            if any(x.project_id != purchase.project_id for x in purchase.launch_ids):
                raise exceptions.ValidationError(_(
                    'The launches must belong to the project.'
                ))
    
    #===== Compute =====#
    def _compute_display_name(self):
        for mo in self:
            mo.display_name = '[{}] {}' . format(mo.name, mo.description) if mo.description else mo.name

    #====== Compute ======#
    @api.depends('amount_untaxed', 'affectation_ids')
    def _compute_warning_budget(self):
        prec = self.env['decimal.precision'].precision_get('Product Price')
        states = ['to approve', 'approved', 'purchase', 'done']
        for purchase in self:
            compare = float_compare(purchase.amount_untaxed, purchase.sum_quantity_affected, precision_digits=prec)
            purchase.warning_budget = purchase.state in states and compare != 0
    
    # --- project_id (shortcut to set line analytic at once on the project) ---
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """ Modify all lines analytic at once """
        project_analytics = self.env.company.analytic_plan_id.account_ids
        for purchase in self:
            purchase.order_line._replace_analytic(
                replaced_ids=project_analytics._origin.ids,
                added_id=purchase.project_id.analytic_account_id._origin.id
            )
    
    #===== Logics =====#
    def _prepare_picking(self):
        """ Write project from PO to procurement group and picking """
        return super()._prepare_picking() | {
            'project_id': self.project_id.id
        }

    def _prepare_invoice(self):
        """ Write project from PO to invoice """
        return super()._prepare_invoice() | {
            'project_id': self.project_id.id
        }
    