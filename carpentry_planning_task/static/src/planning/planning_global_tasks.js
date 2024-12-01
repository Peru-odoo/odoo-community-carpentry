/** @odoo-module **/

import { View } from "@web/views/view";
import { Component, useState } from "@odoo/owl";

export class PlanningGlobalTasks extends Component {
    setup () {
        super.setup();
        this.state = useState({visible: true});
    }
    get projectId() {
        return this.props.model.projectId;
    }

    toggleVisible() {
        this.state.visible = !this.state.visible;
    }

    // Global Tasks list view
    get globalTasksViewProps() {
        const domain = [
            ['project_id', '=', this.projectId],
            ['launch_ids', '=', false],
            ['root_type_id', '=', false]
        ]
        const context = {
            'default_project_id': this.projectId,
            'search_default_open_tasks': true,
            'search_default_closed_last_7_days': true,
        };
        const display = {
            controlPanel: {
                'top-left': false, // title ||| TODO: customizer le titre plutôt que de l'effacer
                'top-right': false, // SearchPanel
                'bottom-left': true, // buttons
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
