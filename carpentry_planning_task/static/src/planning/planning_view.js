/** @odoo-module */

import { PlanningController } from "@carpentry_planning/planning/planning_view";
import { PlanningGlobalTasks } from "./planning_global_tasks";

// Add PlanningGlobalTasks to planning's component
PlanningController.components = {
    ...PlanningController.components,
    PlanningGlobalTasks,
};
