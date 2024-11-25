/** @odoo-module */

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { registry } from '@web/core/registry';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { useService } from '@web/core/utils/hooks';

export class TimesheetKanbanController extends KanbanController {
    setup() {
        super.setup()
        this.actionService = useService('action');
    }

    async onClickViewBudgets() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'carpentry.budget.project',
            name: this.env._t('View Timesheet Budgets'),
            views: [[false, 'pivot']],
            domain: "[('product_id.is_timesheetable', '=', true)]",
            target: 'new'
        });
    }
}

registry.category("views").add("button_view_budget", {
    ...kanbanView,
    Controller: TimesheetKanbanController,
    buttonTemplate: "carpentry_timesheet.KanbanButtons",
});
