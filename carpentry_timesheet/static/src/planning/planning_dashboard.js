/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';

registry.category("carpentry_project.planning_dashboard_item").add(
    "timesheet", {id: "timesheet", title: _lt("Timesheets"), sequence: 30, icon: "fa-clock-o"}
);
