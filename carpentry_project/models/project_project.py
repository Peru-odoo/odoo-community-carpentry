# -*- coding: utf-8 -*-

from odoo import fields, models, exceptions, _
from odoo.tools.safe_eval import safe_eval

def _resolve_string_to_python(string):
    return safe_eval(string) if isinstance(string, str) else string or {}

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

    #===== Button / Action =====#
    def open_project_list_or_form(self):
        project_id_ = self.env['project.default.mixin']._get_project_id()

        # Project List
        if not project_id_:
            # 2 views depending configuration of project's group by stage or not
            group = '_group_stage' if self.env.user.has_group('project.group_project_stages') else ''
            xml_id = 'project.open_view_project_all' + group
            action = self.env['ir.actions.act_window'].sudo()._for_xml_id(xml_id)

            projects_fav = self.env.user._get_favorite_projects()
            # If users has favorite projects, filter the view on them
            if projects_fav.ids:
                context = _resolve_string_to_python(action.get('context'))
                action['context'] = context | {'search_default_my_projects': True}

        # Project Form
        else:
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'project.project',
                'view_mode': 'form',
                'res_id': project_id_,
            }
        
        return action
