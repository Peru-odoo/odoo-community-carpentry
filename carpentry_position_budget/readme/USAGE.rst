



Population of account.move.buget.line from carpentry.position.budget:
- requires configuration of account.move.buget.line.template to define
   an account_id for each analytic_account_id


Merge
*****

Note: when merging positions, only the target positions is kept.
Budget of merged positions is added to this target.
The link with external database, i.e. the ID of the position in the external database,
is explicitely removed when merging, so that the merge operation is not erase
by a new import.
