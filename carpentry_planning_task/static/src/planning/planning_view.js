/** @odoo-module */

import { patch } from '@web/core/utils/patch';
import { PlanningController } from "@carpentry_planning/planning/planning_view";
import { PlanningGlobalTasks } from "./planning_global_tasks";

const planningControllerPatchGlobalTasks = {
    async openRecord (record) {
        if (record._values.can_open) {
            return super.openRecord(record);
        }

        // Open card's tasks if no other card's form to open
        const actionReload = async () => await this.model.load(this.model.root);
        this.actionService.doActionButton({
            type: 'object',
            resModel: 'carpentry.planning.card',
            name: 'action_open_tasks',
            resId: record._values.id,
            context: {'launch_id': this.model.launchId, 'project_id': this.model.projectId},
            onClose: actionReload,
        });
    },
};
patch(PlanningController.prototype, 'planningControllerPatchGlobalTasks', planningControllerPatchGlobalTasks);

// Add PlanningGlobalTasks to planning's component
PlanningController.components = {
    ...PlanningController.components,
    PlanningGlobalTasks,
};
