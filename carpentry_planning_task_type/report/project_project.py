# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions

class Project(models.Model):
    _inherit = ["project.project"]

    def message_post(self, **kwargs):
        """ Waterfall to Tasks the reports sent from Project (with no notification) """
        # Don't send email twice (or more): empty `partner_ids` and prefix `body` with recipients list
        partner_ids_ = kwargs.get('partner_ids')
        task_ids_ = self._context.get('report_task_ids')

        if partner_ids_ and task_ids_:
            partner_ids = self.env['res.partner'].browse(partner_ids_)
            mail_values = kwargs.copy() | {
                'message_type': 'notification',
                'subtype_xmlid': 'mail.mt_note',
                'is_internal': True,
                'partner_ids': []
            }
            if partner_ids.ids:
                mail_values['body'] = _('Send to: %s\n\n', ', ' . join(partner_ids.mapped('name'))) + mail_values.get('body', '')
            
            # Post message (with no mail since no recipients) to Tasks
            task_ids = self.env['project.task'].browse(task_ids_)
            for task in task_ids:
                # mail_post_autofollow: recipients don't subscribe
                task.with_context(mail_post_autofollow=False).message_post(**mail_values)
        return super().message_post(**kwargs)
