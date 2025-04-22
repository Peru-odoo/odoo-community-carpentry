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
    planning_card_color_class = fields.Char(
        # Card Text color. CSS class of "text-bg-xxxxx"
        # Values should be 'muted', 'success', 'warning' or 'danger'
        string='Planning Card Color (class)',
        compute='_compute_planning_card_color_class',
    )
    planning_card_color_int = fields.Integer(
        # Card Left-Bar color. CSS class of "oe_kanban_color_xxxxx"
        compute='_compute_planning_card_color_int',
        string='Planning Card Color (number)',
    )

    @api.model
    def _get_planning_domain(self):
        """ Returns the domain to filter the records to be displayed in the planning view """
        return [('active', '=', True)]

    @api.model
    def _synch_mirroring_column_id(self, column_id):
        """ Must be overwritten for heriting model sourcing 2 columns or more,
            and hold the logic setting `column_id` field on relevant model's records
            (see `project.type` in `carpentry.planning.task.need`)
        """
        pass
    
    #===== Compute =====#
    def _compute_planning_card_color_class(self):
        """ [TO BE OVERWITTEN] """
        self.planning_card_color_class = False
    
    def _compute_planning_card_color_int(self):
        """ Computes `planning_card_color_int` from `planning_card_color_class` as per
            dict `PLANNING_CARD_COLOR`
        """
        for record in self:
            if record.planning_card_color_is_auto:
                color_int = PLANNING_CARD_COLOR.get(record.planning_card_color_class)
                record.planning_card_color_int = color_int

    #===== Button =====#
    def action_open_planning_card(self):
        """ Returns the action to open the planning card view """
        return {
            'type': 'ir.actions.act_window',
            'name': self.display_name,
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
