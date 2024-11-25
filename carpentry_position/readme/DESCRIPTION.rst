
This module extends Project to manage Carpentry Positions and their groupping.
It installs the following data model:

* **Positions**: space reservation of a building plan. It is the smallest organization unit
    in Carpentry Business that lives from sale phase to design, production and installation.
    In combination with `carpentry_budget`, it allows powerful budgetting follow-up at a very
    business-convenient precision.
* **Lots**: grouping of Positions during sale step, not so relevant for project-time but
    is a helpful shortcut for forming the further below groups.
* **Phases**: contractual groupping of Positions with the project's final customer, linked
    with an engaging planning. They corresponds to the installation step of Positions on
    the final building (e.g. frontages). 
* **Launches**: Most important Position's grouping, because the Carpentry Planning
    (see `carpentry_planning`) follows all deadlines and KPI based on Launches.
    They are production-oriented groupping of Positions, and most of the time 1 launch
    triggers 1 subsequent fourniture needs (several purchase orders) and 1 or sub-divided
    fabrication order.
