
This data model allows to prepare in early steps of projects some groups of common tasks
that will be repeated very similarly on every or some launches of the project.


Principle
**********

A *Need Family* is a group of *Needs*, affected to one or several launches.
*Needs* are like template tasks, created within a project and that can be affected
in 1 or several *Need Family* (Many-2-Many relation).


Needs presentation
********************

The *Need Families* only serve to group *Needs* and assign them in mass on one or
several launches. Thus, *Need Families* are only relevant in *Need* menus for
organization and affectation purposes.

However, the *Need Categories*, which is declared directly on *Need*, is used to
present and organize the needs on Carpentry Planning.

While creating and naming *Need Families* is fully open, and organized per projects,
the *Need Categories* are items managed at company level.

Finally, *Need Types* is only about organizing *Need Categories* within `project.type`.
It is however highly important because used to discrepency *Needs* in right
Carpentry Planning's column.
