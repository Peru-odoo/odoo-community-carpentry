

Needs lifecycle: from Needs Families to assigned Tasks
*******************************************************

#. At first, a *Need* is created within a project and assigned to a *Need Family*.
   This has no impact on project's tasks yet.
#. When a *Need Family* is affected to one or several launches, it converts all its
   *Needs* into mirroring *Tasks* (of `type=need`). There are 1 mirroring *Tasks*
   per each need **and** launch in the affectation. Those tasks are not assigned to
   any users yet. They are affected to a single launch, and their their deadline
   are computed in retro-planning based on their Launch's production start date.
   Modification of those tasks is allowed, but for removal the users must act on
   *Need* or *Need family*
#. Then, when a *Task* of `type=need` is assigned to a user, its deadline stops
   following launch's production start date and can be modified manually.
   All other information of the *Task* stay the same, and it keeps being listed in
   the same views. 


Tutorial
*******************************************************

Create and affect:

#. Open *Project* application and create a Project
#. Browse to the menu-item *Needs/Create and affect needs* and create a new need family.
#. Create a first *Need Familiy*, and add *Needs* into it.
#. Since no there is not existing *Need* on the project, you may create a few.
#. When creating a new *Need*, you choose the number of weeks before the
   launch's production start date it must be realized, and its *Need Category*.
#. Start creating another *Need Family*: you may re-use *Needs* created on the
   first *Need Family*.
#. You may also duplicate *Need Families*, and only customize the *Needs* in it.
#. On *Need Family* forms, you may affect a *Need Family* to one or several launches.
   This action will create 1 mirroring tasks in the project, per launch and *Need*
   in the *Need Family*.

View and adjust:

#. Browse to the menu-item *Needs/View and adjust needs*. This view displays the
   mirroring tasks created when affecting a *Need Family* to a Launch.
#. You may directly create *Tasks* of `type=need` and skip *Need Family* grouping
   and affectation mechanism. Those taasks will similarly have a deadline based on
   launch's production start date (**N weeks** before it).
