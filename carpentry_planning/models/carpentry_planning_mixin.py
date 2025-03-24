# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command

PLANNING_CARD_COLOR = {
    'muted': 0, # info: 4
    'warning': 2,
    'success': 10, # 20
    'danger': 9, # 23
}

class CarpentryPlanningMixin(models.AbstractModel):
    """ To be inherited of models that can be Carpentry Planning's columns """
    _name = "carpentry.planning.mixin"
    _description = 'Planning Mixin'

    active = fields.Boolean(default=True)
    planning_card_color_is_auto = fields.Boolean(
        # If `True`, card color cannot be chosen from planning's card dropdown menu
        #   and `planning_card_color_int` field is computed from `planning_card_color_class`
        # If `False', `planning_card_color_int` field should be stored 
        default=True,
        store=False
    )
    planning_card_color_class = fields.Selection(
        # Card Text color. CSS class of "text-bg-xxxxx"
        # Should be overwritten with a `compute` or `related`
        string='Planning Card Color (class)',
        selection=[
            ('muted', 'Grey'),
            ('success', 'Green'),
            ('warning', 'Orange'),
            ('danger', 'Red')
        ],
        store=False
    )
    planning_card_color_int = fields.Integer(
        # Card Left-Bar color. CSS class of "oe_kanban_color_xxxxx"
        compute='_compute_planning_card_color_int',
        string='Planning Card Color (number)',
    )

    @api.model
    def _synch_mirroring_column_id(self, column_id):
        """ Must be overwritten for heriting model sourcing 2 columns or more,
            and hold the logic setting `column_id` field on relevant model's records
            (see `project.type` in `carpentry.planning.task.need`)
        """
        pass
    
    # for column headers (in place of <progressbar />)
    @api.model
    def _get_planning_subheaders(self, column_id, launch_id):
        """ Returns short text and budget infos (spent / available), to display in planning column header
            Output example:
                'description': 'something',
                'budgets': [{
                    'icon': 'fa fa-clock-o',
                    'tooltip': 'Hello',
                    'unit': 'h',
                    'spent': 5.0,
                    'available': 10.0,
                }]
        """
        return {}

    #===== Compute =====#
    def _compute_planning_card_color_int(self):
        """ Computes `planning_card_color_int` from `planning_card_color_class` as per
            dict `PLANNING_CARD_COLOR`
        """
        for record in self:
            if record.planning_card_color_is_auto:
                color_int = PLANNING_CARD_COLOR.get(record.planning_card_color_class)
                record.planning_card_color_int = color_int
