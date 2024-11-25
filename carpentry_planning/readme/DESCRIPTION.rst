
-----------------
Technical choices
-----------------

Specificities:

* Each column's data comes from a different model.

  *Choice*: align models (`carpentry.planning.mixin`) on a few columns name and use a view to
  gather data to be loaded by Kanban view (`carpentry_planning_card`)

* Search in left pannel on `launch_ids` is needed, in form of `multi=one` which is not supported
  (searchpannel's field must be stored and O2m can only be `select="multi"`). Futhermore, *"Needs"*
  columns (only) must ignore filters on projects and launches.

  *Choice*: and `launch_ids` as computed fields in model `carpentry_planning_card`.
  Build a custom Search Pannel that will manage the search domain bar.
  Use a `_search_...` method to filter on them, which ignores the filter for needs
  (ie. records of `project.type` model).  Custom search pannel is also used to display project's
  Global Tasks, indepently of filters and Kanban view.

* Add top-banner for KPIs and left pannel for custom search.

  *Choice*: extend Kanban View (`js_class="carpentry_planning_kanban"`) to add them around
  Kanban Renderer component (HTML+CSS).

* Content of Kanban cards depends on search domain, for tasks, performance (and, only for needs,
  the card color).

  *Choice*: also extend Kanban Records JS component and make a custom/dedicated ORM call for tasks.



Carpentry Needs specificities (i.e. 1 model for twice or more columns)
***********************************************************************

Reference field `identifier_ref` on `carpentry.planning.column` may manually be changed by users.
It points out the ID of the record of a table able to filter which records goes to which column.

The logic of filtering must be held on the model of `identifier_res_model`.
This model must have a `column_id` field, 
