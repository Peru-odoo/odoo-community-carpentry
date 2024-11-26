# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.osv import expression

from collections import defaultdict
import datetime

class Project(models.Model):
    _inherit = ["project.project"]

    def _compute_display_name(self):
        """ Add current week to display_name """
        super()._compute_display_name()
        
        if self._context.get('display_with_week'):
            for project in self:
                project.display_name += _(
                    ' (W%s)', fields.Date.context_today(self).isocalendar()[1]
                )
    
    def get_planning_dashboard_data(self):
        """ To be overritten to add Cards in project's top-bar dashboard """
        return {}
