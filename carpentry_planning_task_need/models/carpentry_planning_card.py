# -*- coding: utf-8 -*-

from odoo import models, fields

class CarpentryPlanningCard(models.Model):
    """ Add required field for specific Tasks cards """
    _inherit = ["carpentry.planning.card"]

    #===== ORM methods =====#
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ All needs in a column can be archived:
            `active_test` must be disabled to find them in `read_group()`
        """
        return super(
            CarpentryPlanningCard, self.with_context(active_test=False)
        ).read_group(domain, fields, groupby, offset, limit, orderby, lazy)

    #===== Fields =====#
    project_task_id = fields.Many2one(
        # for research by launches
        comodel_name='project.task',
        string='Task',
    )

    user_ids = fields.Many2many(
        comodel_name='res.users',
        compute='_compute_fields'
    )
    week_deadline = fields.Integer(compute='_compute_fields')
    week_end = fields.Integer(compute='_compute_fields')
    type_name = fields.Char(compute='_compute_fields')
    
    #===== Compute =====#
    def _get_fields(self):
        return super()._get_fields() + ['user_ids', 'week_deadline', 'week_end', 'type_name']

    # @api.model
    # def _search_launch_ids(self, operator, value):
        # """ Sticky Needs: don't filter by project (independant of filtered launch) """
        # return expression.OR([
        #     [('project_id', '=', False)],
        #     [(field, operator, value) for field in fields]
        # ])
    
    #===== Button =====#
    def action_activate_need(self):
        task = self.env['project.task'].browse(self.res_id)
        return task.action_activate_need()
