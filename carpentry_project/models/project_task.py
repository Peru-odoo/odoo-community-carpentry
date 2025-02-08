# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class ProjectTask(models.Model):
    _inherit = ["project.task"]

    def copy(self, default=None):
        res = super().copy(default)

        suffix = _(" (copy)")
        if res.name.endswith(suffix):
            res.name = res.name.removesuffix(suffix)
        
        return res
