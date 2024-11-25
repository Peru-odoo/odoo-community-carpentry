/** @odoo-module */

import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useService } from '@web/core/utils/hooks';

export class PlanSetListController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService('action');
        
    }
    
    async onClickNewPlanSet() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: this.env._t('New Planset'),
            res_model: 'carpentry.plan.set',
            views: [[false, 'form']],
            target: 'new'
        });
    }
}

registry.category("views").add("carpentry_design_release_tree", {
    ...listView,
    Controller: PlanSetListController,
    buttonTemplate: "carpentry_design.ListButtons",
});
