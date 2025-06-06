/** @odoo-module */

import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useService } from '@web/core/utils/hooks';

export class GroupListController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService('action');
    }


    // async actionQuickCreate() {
    //     const actionReload = async () => await this.actionService.doAction({
    //         'type': 'ir.actions.client',
    //         'tag': 'soft_reload'
    //     });

    //     this.actionService.doActionButton({
    //         type: 'object',
    //         name: 'button_group_quick_create',
    //         resModel: this.env.model.root.resModel,
    //         onClose: actionReload,
    //         context: this.env.model.root.context,
    //     });
    // }

    async openAffectationMatrix() {
        this.actionService.doActionButton({
            type: 'object',
            name: 'button_open_affectation_matrix',
            resModel: this.env.model.root.resModel,
            context: this.env.model.root.context,
        });
    }
}

registry.category("views").add("carpentry_position_group", {
    ...listView,
    Controller: GroupListController,
    buttonTemplate: "carpentry_position_group.ListButtons",
});
