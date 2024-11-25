# -*- coding: utf-8 -*-

from odoo import fields, models, exceptions, _

class ProjectProject(models.Model):
    _inherit = ["project.project"]

    #===== Fields =====#
    # User-interface
    warning_banner = fields.Boolean(
        compute='_compute_warning_banner'
    )
    
    #===== Compute =====#
    def _compute_warning_banner(self):
        for project in self:
            project.warning_banner = project._get_warning_banner()
    def _get_warning_banner(self):
        """ Inherite to add conditions to display the warning banner """
        self.ensure_one()
        return False
