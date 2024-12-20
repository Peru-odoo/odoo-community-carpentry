# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons.carpentry_planning_task_type.models.project_task import (
    XML_ID_INSTRUCTION, XML_ID_MILESTONE, XML_ID_MEETING
)

from collections import defaultdict
import datetime

class Project(models.Model):
    _inherit = ['project.project']

    instruction_count = fields.Integer(
        string="Instructions",
        compute='_compute_instruction_count'
    )

    def _compute_instruction_count(self):
        domain = [('project_id', 'in', self.ids), ('root_type_id', '=', self.env.ref(XML_ID_INSTRUCTION).id)]
        rg_result = self.env['project.task'].sudo().read_group(
            domain=domain,
            fields=['instruction_count:count(id)'],
            groupby=['project_id']
        )
        mapped_count = {x['project_id'][0]: x['instruction_count'] for x in rg_result}
        for project in self:
            project.instruction_count = mapped_count.get(project.id, 0)


    #===== Planning =====#
    def get_planning_dashboard_data(self):
        """ Data for project's dashboard KPI """
        return (
            super().get_planning_dashboard_data()
            | self._get_planning_dashboard_task_meetings()
            | self._get_planning_dashboard_task_milestones()
        )

    def _get_planning_dashboard_task_meetings(self):
        fields = ['id', 'display_name', 'kanban_state', 'count_message_ids', 'message_last_date']
        meeting_ids = self.task_ids.filtered(
            lambda x: x.root_type_id.id == self.env.ref(XML_ID_MEETING).id
        ).sorted(
            key=lambda r: r.message_last_date or datetime.date.max,
            reverse=True
        )
        return {'meetings': meeting_ids.read(fields)}

    def _get_planning_dashboard_task_milestones(self):
        # parent_types
        fields = ['id', 'name', 'shortname']
        domain = [
            ('root_type_id', '=', self.env.ref(XML_ID_MILESTONE).id),
            ('task_ok', '=', False)
        ]
        parent_types_data = self.env['project.type'].sudo().with_context(display_short_name=True).search_read(domain, fields)

        # milestones, groupped by `parent_type_id`
        fields = ['id', 'display_name', 'kanban_state', 'date_deadline', 'date_end', 'parent_type_id']
        domain = [
            ('root_type_id', '=', self.env.ref(XML_ID_MILESTONE).id),
            ('project_id', 'in', self.ids)
        ]
        milestones_data = self.env['project.task'].search_read(domain, fields, order='type_sequence')

        mapped_milestone_data = defaultdict(list)
        for x in milestones_data:
            parent_type_id = x['parent_type_id'][0]
            del(x['parent_type_id'])

            x['week_deadline'] = bool(x['date_deadline']) and x['date_deadline'].isocalendar()[1]
            mapped_milestone_data[parent_type_id].append(x)
        
        return {
            'parent_types': parent_types_data, # 1st line (columns header)
            'milestones': mapped_milestone_data # rows
        }
