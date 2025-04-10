/** @odoo-module **/

import { View } from "@web/views/view";
import { Component, useState } from "@odoo/owl";

export class PlanningGlobalTasks extends Component {
    setup () {
        super.setup();
        this.state = useState({visible: true});
    }
    get projectId() {
        return this.props.model.projectId || 0;
    }

    toggleVisible() {
        this.state.visible = !this.state.visible;
    }

    // Global Tasks list view
    get globalTasksViewProps() {
        const domain = [
            ['project_id', '=', this.projectId],
            ['launch_id', '=', false],
            ['root_type_id', '=', false],
            ['allow_timesheets', '=', false]
        ]
        const context = {
            'default_project_id': this.projectId,
            'search_default_open_tasks': true,
            'search_default_closed_last_7_days': true,
        };
        const display = {
            controlPanel: {
                'top-left': false, // title ||| TODO: customizer le titre plutôt que de l'effacer
                'top-right': true, // SearchPanel
                'bottom-left': true, // buttons
                'bottom-left-buttons': true, // dropdown action button
                'bottom-right': true, // searchMenuTypes
            }
        }
        const viewProps = {
            resModel: 'project.task',
            type: 'list',
            limit: 15,
            display,
            domain,
            context,
            loadActionMenus: true,
            useSampleModel: false
        };

        return viewProps;
    }
}

PlanningGlobalTasks.template = "carpentry_planning_task.PlanningGlobalTasks";
PlanningGlobalTasks.components = { View };
PlanningGlobalTasks.props = {
    model: true
};
