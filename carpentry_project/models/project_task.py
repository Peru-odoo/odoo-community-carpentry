# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.tools import html2plaintext, plaintext2html

class ProjectTask(models.Model):
    _inherit = ["project.task"]

    # -- ui field --
    description_text = fields.Text(
        # allow displaying Description in Tree view though it's HTML field
        compute='_compute_description_text',
        inverse='_inverse_description_text'
    )

    kanban_state = fields.Selection(compute=False)
    create_date_week = fields.Char(
        string='Create Week',
        compute='_compute_create_date_week'
    )
    date_deadline = fields.Datetime(string='Deadline')
    date_end = fields.Datetime(string='Finish Date')

    #===== CRUD =====#
    def copy(self, default=None):
        res = super().copy(default)

        suffix = _(" (copy)")
        if res.name.endswith(suffix):
            res.name = res.name.removesuffix(suffix)
        
        return res
    
    #===== Compute (html's `description` to `description_text`) =====#
    @api.depends('description')
    def _compute_description_text(self):
        for task in self:
            task.description_text = html2plaintext(task.description or '')
    def _inverse_description_text(self):
        for task in self:
            task.description = plaintext2html(task.description_text or '')
    
    #===== Compute dates =====#
    @api.depends('create_date')
    def _compute_create_date_week(self):
        for task in self:
            date = task.create_date
            task.create_date_week = bool(date) and _('W%s', str(date.isocalendar()[1]))
    
    #===== Compute `stage_id` depending `date_end` =====#
    @api.depends('date_end')
    def _compute_stage_id(self):
        """ == Overwrite Odoo method ==
            When user set `date_end` consider the tasks as done
        """
        res = self._get_stage_open_done()
        for task in self:
            is_closed = bool(task.date_end)
            has_changed = is_closed != task.is_closed
            task._change_state_one(has_changed, is_closed, *res)
    
    def _get_stage_open_done(self):
        stage_ids = self.env['project.task.type'].search([])
        stage_open = fields.first(stage_ids.filtered_domain([('fold', '=', False)]))
        stage_done = fields.first(stage_ids.filtered_domain([('fold', '=', True)]))
        return stage_open, stage_done
    
    def _change_state_one(self, has_changed, is_closed, stage_open, stage_done):
        """ Move to Open or Closed stage """
        self.ensure_one()
        if has_changed:
            if is_closed:
                self.stage_id = stage_done.id
                self.kanban_state = 'done'
                self.date_end = fields.Datetime.now()
            else:
                self.stage_id = stage_open.id
                self.kanban_state = 'normal'
                self.date_end = False
        return has_changed and is_closed

    #===== Button =====#
    def button_toggle_done(self):
        self.ensure_one()
        stages = self._get_stage_open_done()
        self._change_state_one(True, not self.is_closed, *stages)
    
    #===== Task copy =====#
    def _fields_to_copy(self):
        return super()._fields_to_copy() | ['card_res_id', 'card_res_model']
    