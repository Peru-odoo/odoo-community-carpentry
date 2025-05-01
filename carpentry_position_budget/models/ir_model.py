# -*- coding: utf-8 -*-

from odoo import models, api

class IrModel(models.Model):
    _inherit = ['ir.model']

    def name_get(self):
        """ On carpentry report, it's needed to group budget between Project & Launch/Phase
            We want `name` to be shown to user, not `model`
        """
        if self._context.get('display_model_shortname'):
            res = []
            for model in self:
                res.append((model.id, model.name))
            return res
        
        return super().name_get()
