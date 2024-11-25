
This module tries facilitating Odoo standard workflow for carpentry / construction vertical.

Carpentry / construction projects presale lifecycle slightly differs from Odoo standard
workflow. In Odoo standard, an opportunity generates quotations and sales, and then
projects and tasks. In construction projects, a won opportunity becomes a project, which then
generate income (quotation and sale) like monthly client invoices (situations).

In business terms, this module combined with `carpentry_position_budget` and
`carpentry_budget_progress` allows to manage:

#. **Market saled to a client on a project**: amount of the initial contract
#. **Budgets associated to initial market (fully in `carpentry_position_budget`)**:
   internal real estimated cost to realize the project for the construction company
   using Odoo
#. **Market evolutions**: market plus its amendments ; in discussions (quotations)
  or validated (sales orders)
#. **Follow up of budget consumption progress (fully in `carpentry_budget_progress`)**:
  to estimate a % of real-work progress on all costs centers (i.e. project's budgets)
  and estimate real-time Profits & Losses without waiting accounting's project balance
#. **Real costs**: splitted in differents costs centers (or budgets). Where Odoo foresee
  1 budget per project, it allows managing many, like:
    * tasks timesheets (offices)
    * production timesheets (manufacturing)
    * purchases of goods, services and fees (Odoo's standard)

See also `carpentry_warranty_aftersale` for construction warranty (*Garantie de parfait
achèvement (GPA)* in French) and aftersale (petites affaires *Service après-vente* in
French).
