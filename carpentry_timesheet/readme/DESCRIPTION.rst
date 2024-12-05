
=============
Main features
=============

This module largely relies on the native timesheet feature of Odoo CE and OCA,
and custom modules `project_budget_timesheet`, `project_task_analytic_hr` and
`project_task_analytic_type`.

Key adaptation of this module is setting a Task analytic account to **1 budget
within its project**, instead of *the project's analytic account* itself (native
behavior), and adding a dedicated view accessible via *Project / Budget /
Timesheet's budget*.


Customization of Odoo CE or OCA modules
***************************************

#. Lock usage of *Analytic Account* field of *Tasks* to use timesheetable budgets
    * Technically: this is helpful because timesheets will belong to this analytic
      plan instead of project's
    * Note: the `project_id` is still natively available in the model
      `account.analytic.line` (timesheets)

#. `hr_timesheet_sheet`: make tasks required

#. Add a (timesheet) *Performance %* widget next to existing timesheet widget on all
   all Tasks kanban cards, and Carpentry Planning cards


Carpentry Features
******************

* Entry menu *Project / Budget / Timesheet's Budget* displaying tasks filtered on those
  with budget or timesheets. This view helps:
    * creating budget-specific tasks (context key `default_planned_hours_required`)
    * viewing available timesheetable project's budget (special button *View Budgets*)
