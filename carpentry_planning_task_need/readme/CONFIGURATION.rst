
Planning's column
****************************

The Carpentry Planning can have several columns fetching records from the same model
`project.type`. To route the needs between the right planning's column,
the field `parent_type_id` of `project.type` is the pivot configured on planning's column.
E.g. of pivot: *"Need (method)"*

Any changes in planning's columns configuration is taken into account immediatly.

To fit with Planning requirements, the Task's Types structure for needs should
follow this schema:
* `need`
   * `need_method`
      * Aluminium
      * Debit
      * ...
   * `need_construction`
      * Support reception
      * Instructions for installation
      * ...


Need reference date
****************************

The field `column_id_need_date` is added to `carpentry.planning.column` model.
This configuration holds the column (if different than the current) whose `start`
milestone will be used as date reference for the retro-planning calculation
of needs objectif date.

*Example : needs on a "Method" column must have their objective dates calculated as per
"Production" column's start date milestone.*


Need Categories
***************

*Need Categories* actually are children *Tasks Types* of the task type with XML_ID `task_type_need`.
On *Project / Configuration / Project Types*, you may view and modify the *Need Categories*.
Note: deletion of root types is prevented by design.
For need, deletion of middle-level types will be prevented too, since they are linked to
Carpentry Column's planning.


Need Type, filtering & roles
****************************

Since each users is especially interested into 1 need category, the filter `filter_my_role`
is enabled by default on domain search of *Need Family* and *View Need* (tasks) views.
To do so, one rely on the feature of module `project_task_default_assignee`, which
links a type to 1 role (and roles are assigned to users in project).
**Defect warning:** as soon as a user is affected to a role in 1 project, it sees all
the need related to this role on all projects.
