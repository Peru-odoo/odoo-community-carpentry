
--------------------------------
Example of planning columns data
--------------------------------

Sub-modules may have a **carpentry.planning.column.csv** file, loading data of exampel shown below.
However, in order for the changes to apply, the module `carpentry_planning` must be upgraded.

id,name,res_model,identifier_res_model_id:id,identifier_res_id:id,sequence,fold,icon
planning_column_need_method,Needs (Method),project.type,model_project_role,carpentry_planning_task_need.project_role_project,20,False,fa fa-eye
planning_column_need_field,Needs (Field),project.type,model_project_role,carpentry_task_need.project_role_field,60,False,fa fa-building-o