# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command

class CarpentryPlanningMixin(models.AbstractModel):
    """ To be inherited of models that can be Carpentry Planning's columns """
    _name = "carpentry.planning.mixin"
    _description = 'Planning Mixin'

    active = fields.Boolean(default=True)
    planning_card_color = fields.Integer(
        string='Planning Card Color',
        default=False
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
