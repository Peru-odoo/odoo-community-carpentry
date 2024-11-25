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
        return (
            super().get_planning_dashboard_data()
            | self._get_planning_dashboard_task_data()
        )

    def _get_planning_dashboard_task_data(self):
        """ Data for project's dashboard KPI """
        
        domain = [('root_type_id', '=', self.env.ref(XML_ID_MILESTONE).id)]
        type_ids = self.env['project.type'].sudo().search(domain)
        meeting_ids = self.task_ids.filtered(
            lambda x: x.root_type_id.id == self.env.ref(XML_ID_MEETING).id
        ).sorted(
            key=lambda r: r.message_last_date or datetime.date.max,
            reverse=True
        )
        milestone_ids = self.task_ids.filtered(
            lambda x: x.root_type_id.id == self.env.ref(XML_ID_MILESTONE).id
        ).sorted('type_sequence')

        # select fields
        fields_type = ['id', 'name', 'shortname']
        fields_meeting = ['id', 'display_name', 'kanban_state', 'count_message_ids', 'message_last_date']
        fields_milestone = ['id', 'display_name', 'kanban_state', 'date_deadline', 'date_end', 'type_id']
        # reformat/group milestones
        mapped_milestone_data = defaultdict(list)
        for data in milestone_ids.read(fields_milestone):
            type_id = data['type_id'][0]
            del(data['type_id'])

            data['week_deadline'] = bool(data['date_deadline']) and data['date_deadline'].isocalendar()[1]
            mapped_milestone_data[type_id].append(data)
        
        return {
            'types': type_ids.read(fields_type),
            'meetings': meeting_ids.read(fields_meeting),
            'milestones': {type.id: mapped_milestone_data.get(type.id, []) for type in type_ids}
        }
