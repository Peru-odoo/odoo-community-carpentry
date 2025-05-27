# -*- coding: utf-8 -*-

from os import name
from odoo import api, fields, models, _, exceptions

class PurchaseRequisition(models.Model):
    _name = "purchase.requisition"
    _inherit = ["purchase.requisition", "project.default.mixin"]
    _rec_names_search = ['name', 'title']

    #===== Fields methods =====#
    @api.depends('name', 'title')
    def _compute_display_name(self):
        for requisition in self:
            requisition.display_name = (
                '[{}] {}' . format(requisition.name, requisition.title)
                if requisition.title
                else requisition.name
            )

    #===== Fields =====#
    title = fields.Char(string='Title', translate=True)
    project_id = fields.Many2one(required=False)

    #===== Onchange =====#
    def _onchange_vendor(self):
        """ Don't return anything => skip warning of several open blanket per supplier """
        super()._onchange_vendor()

    #===== Button =====#
    def action_in_progress(self):
        """ Allow requisitions without products """
        self.ensure_one()
        # [modified] removed lines here
        if self.type_id.quantity_copy == 'none' and self.vendor_id:
            for requisition_line in self.line_ids:
                if requisition_line.price_unit <= 0.0:
                    raise UserError(_('You cannot confirm the blanket order without price.'))
                if requisition_line.product_qty <= 0.0:
                    raise UserError(_('You cannot confirm the blanket order without quantity.'))
                requisition_line.create_supplier_info()
            self.write({'state': 'ongoing'})
        else:
            self.write({'state': 'in_progress'})
        # Set the sequence number regarding the requisition type
        if self.name == 'New':
            self.name = self.env['ir.sequence'].with_company(self.company_id).next_by_code('purchase.requisition.blanket.order')