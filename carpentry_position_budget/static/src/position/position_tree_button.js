/** @odoo-module */

import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useService } from '@web/core/utils/hooks';

export class PositionListController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService('action');
    }

    async openPositionBudget() {
        this.actionService.doAction('carpentry_position_budget.action_open_position_budget_srv');
    }
    async openImportWizard() {
        this.actionService.doAction('carpentry_position_budget.action_open_position_budget_import_wizard');
    }
}

registry.category("views").add("carpentry_position_budget", {
    ...listView,
    Controller: PositionListController,
    buttonTemplate: "carpentry_position_budget.ListButtons",
});
