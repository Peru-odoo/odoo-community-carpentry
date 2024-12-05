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
            res_model: 'account.move.budget.line',
            name: this.env._t('Project Budgets for Timesheets'),
            views: [
                [false, 'pivot'],
                [false, 'graph'],
                [false, 'tree'],
            ],
            domain: "[('analytic_account_id.timesheetable', '=', true)]",
            target: 'new'
        });
    }
}

registry.category("views").add("carpentry_timesheet_button", {
    ...kanbanView,
    Controller: TimesheetKanbanController,
    buttonTemplate: "carpentry_timesheet.KanbanButtons",
});
