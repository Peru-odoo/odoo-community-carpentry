# -*- coding: utf-8 -*-

from odoo import fields, models, exceptions, _

class ProjectChoiceWizard(models.TransientModel):
    _inherit = ['project.choice.wizard']

    def open_project_list_or_form(self):
        """ This (ugly) proxy-method is needed because:
            * server action requires WRITE permission on the model to be called (!!!)
            * `project.group_project_user` must stay with READ only on `project.project`
        """

        return self.env['project.project'].sudo().open_project_list_or_form()
