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
        const additionalContext = this.env.model.root.context;
        this.actionService.doAction(
            'carpentry_position_budget.action_open_position_budget_srv',
            {additionalContext}
        );
    }
    async openImportWizard() {
        const additionalContext = this.env.model.root.context;
        this.actionService.doAction(
            'carpentry_position_budget.action_open_position_budget_import_wizard',
            {additionalContext}
        );
    }
}

registry.category("views").add("carpentry_position_budget", {
    ...listView,
    Controller: PositionListController,
    buttonTemplate: "carpentry_position_budget.ListButtons",
});
