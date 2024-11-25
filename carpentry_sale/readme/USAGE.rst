
In details, this module brings the following changes.

**Sale Order's Form and Tree**

* add `Name`, `Attachments` and `Internal Note` field
* Add `Validated?` field on Sale Order lines and modification of sale order's total
  calculation:
    * validated lines only (in native Odoo total field)
    * all lines (in a new fields)
  If all lines are not *Validated* when validating a Sale Order, a informative
  message is shown to the user proposing to her/him to automatically move all
  lines to validated or continue as-is.

* Filters and status on Sale Order tree about partial-validated SO


**Project's & Task's Form**

* Add `Market`, `Validated sales orders lines` and `Reviewed market` total fields below `Opportunity`
* The smart button towards Quotations & Sale Order displays a warning (orange) when all project's SO lines
  are not validated
* Hide `Sale Order Line` on Tasks' form
