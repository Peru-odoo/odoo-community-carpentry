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
    task_ids = fields.One2many(related='launch_ids.task_ids')
    # -- ui --
    warning_stock = fields.Boolean(compute='_compute_warning_stock')
    
    #===== Compute =====#
    def _compute_display_name(self):
        for mo in self:
            mo.display_name = '[{}] {}' . format(mo.name, mo.description) if mo.description else mo.name

    #====== Compute ======#
    @api.depends('order_line', 'order_line.product_id', 'order_line.product_id.type')
    def _compute_warning_stock(self):
        """ Display a warning banner if purchase has both storable and consummable products """
        for purchase in self:
            both_types = all(x in purchase.order_line.product_id.mapped('type') for x in ['consu', 'product'])
            purchase.warning_stock = both_types
    
    # --- project_id (shortcut to set line analytic at once on the project) ---
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """ Modify all lines analytic at once """
        project_analytics = self.env.company.analytic_plan_id.account_ids
        for purchase in self:
            purchase._ensure_project_launches_consistency()
            project_id = purchase.project_id.analytic_account_id._origin.id
            purchase.order_line._replace_analytic(
                replaced_ids=project_analytics._origin.ids,
                new_distrib={project_id: 100} if project_id else {},
                analytic_plan='project',
            )
    
    def _ensure_project_launches_consistency(self):
        """ Launch_ids must belong to the project
            (a discrepency could happen since `project_id` can be modified)
        """
        self.ensure_one()
        to_clean = self.launch_ids.filtered(lambda x: x not in self.project_id.launch_ids)
        if to_clean:
            self.launch_ids -= to_clean
    
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
