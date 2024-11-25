# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command
from odoo.osv import expression

from collections import defaultdict
import datetime

class Project(models.Model):
    _inherit = ["project.project"]

    this_week = fields.Char(
        # for srv action to open planning
        default=lambda self: fields.Date.context_today(self).isocalendar()[1]
    )
    
    def get_planning_dashboard_data(self):
        """ To be overritten to add Cards in project's top-bar dashboard """
        return {}
