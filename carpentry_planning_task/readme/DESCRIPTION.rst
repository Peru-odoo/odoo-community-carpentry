
This module allows to manage from the Carpentry Planning all the projects tasks.
It mainly adds 2 features in the Carpentry Planning:

* a *Global Tasks* tree view above Carpentry Planning's kanban, on the
  page so everything is available without browsing to another menu
* a *Tasks widget* on planning's cards, visible on card's mouse hover. Widget's
  is colored depending cards tasks states. The tasks list of a card is also
  accessible on widget's click.

Furthermore:

* a Reference field is added on task' form, so end-user may link tasks to Carpentry
  Planning's card for the task's form itself. It is exactly the same han creating
  tasks from a Carpentry Planning's card
* logics of `date_end` is extended so the date is updated to *today* when `kanban_state`
  changes to *done*, and the reverse, i.e. `kanban_state` is moved to *done* when
  `date_end` is changed. This allows easily keeping trace of tasks' completion date, while
  standard Odoo logics updates `date_end` only when tasks moves to *closed* stages

This module can be extended with `carpentry_task_budget` and `carpentry_planning_task_need`.
