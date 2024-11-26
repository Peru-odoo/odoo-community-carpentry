/** @odoo-module */

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { PlanningModel } from "./planning_model";
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

import { PlanningDashboard } from "./planning_dashboard";
import { PlanningLeftSidePanel } from "./planning_left_side_panel";

// ===== Renderer =====
export class PlanningKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        this.actionService = useService('action');
    }
    openMilestone(milestone) {
        this.actionService.doAction({
            'type': 'ir.actions.act_window',
            'res_model': 'carpentry.planning.milestone',
            'res_id': milestone.id,
            'name': milestone.name,
            'views': [[false, 'form']],
            'target': 'new',
        }, {
            onClose: async () => await this.props.list.model.load(this.props.list)
        });
    }
}
PlanningKanbanRenderer.template = "carpentry_planning.PlanningKanbanRenderer";

// ===== Controller =====
export class PlanningController extends KanbanController {
    setup() {
        super.setup();
        this.archInfo = {...this.props.archInfo};
        this.archInfo.className += " flex-grow-1"; // for Kanban flex layout with left side panel
        
        // Custom Layout: only display Breadcrumbs
        this.display = this.props.display;
        this.display.controlPanel = {
            ...this.display.controlPanel,
            'top-right': false, // SearchPanel
            'bottom-right': false, // searchMenuTypes
            'bottom-left': false, // buttons
        };
    }

    // Kanban (planning) - overwrites card opening
    async openRecord (record) {
        // Open card's form if specified
        if (!record._values.can_open) {
            return
        }
        const actionReload = async () => await this.model.load(this.model.root);

        // Specific form related to the card's model
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: record._values.res_model,
            res_id: record._values.res_id,
            name: record._values.display_name,
            views: [[false, 'form']],
            target: 'new',
        }, {onClose: actionReload});
    }
}
PlanningController.template = "carpentry_planning.CarpentryPlanningKanbanView"
PlanningController.components = {
    ...KanbanController.components,
    PlanningKanbanRenderer,
    PlanningDashboard,
    PlanningLeftSidePanel,
};

// ===== View =====
export const carpentryPlanningKanbanView = {
    ...kanbanView,
    Renderer: PlanningKanbanRenderer,
    Controller: PlanningController,
    Model: PlanningModel
};

registry.category("views").add("carpentry_planning_kanban", carpentryPlanningKanbanView);

