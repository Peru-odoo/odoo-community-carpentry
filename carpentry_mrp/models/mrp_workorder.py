# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class MrpWorkorder(models.Model):
    _inherit = ["mrp.workorder"]
    _rec_names_search = ['name', 'production_id', 'workcenter_id', 'project_id']

    #===== Fields methods =====#
    def name_get(self):
        if self._context.get('workorder_display_name_simple'):
            return super().name_get()
        
        res = []
        for wo in self:
            index = wo.production_id.workorder_ids.ids.index(wo._origin.id) + 1
            res.append((wo.id, "%s - %s - %s" % (
                wo.production_id.display_name,
                wo.workcenter_id.display_name,
                wo.name,
            )))
        
        return res
    