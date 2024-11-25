# -*- coding: utf-8 -*-
from odoo import api, tools, fields, models

class TimesheetsAnalysisReport(models.Model):
    _inherit = "timesheets.analysis.report"

    product_id = fields.Many2one("product.product", string="Product", readonly=True)

    @api.model
    def _select(self):
        return super()._select() + ", A.product_id AS product_id"
