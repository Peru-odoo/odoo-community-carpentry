/** @odoo-module **/

import { registry } from '@web/core/registry';
import { _lt } from "@web/core/l10n/translation";

//===== Tasks items =====
const dashboardItems = [
    {id: "meeting", title: _lt("Meetings"), sequence: 10, icon: "fa-calendar"},
    {id: "milestone", title: _lt("Milestones"), sequence: 20, icon: "fa-flag"},
];
dashboardItems.forEach(item => {
    registry.category("carpentry_planning.planning_dashboard_item").add(item.id, item);
});
