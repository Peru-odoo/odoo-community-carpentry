
=============
Main features
=============

todo

- filtre purchase par projet
[TODO: quand le travail sur les PO sera fait, préciser le comportement/choix possible (lieu de livraison)]


Customization of Odoo CE or OCA modules
***************************************

* Uses module `project_purchase_link`, and adapts smart buttons on project's form
  to only show 2 buttons *Purchases* and *Purchase Invoices* (hides buttons towards
  lines)


Carpentry Features
******************

* Adds on Purchase Order form the fields for Project, Launchs and a name of the PO.
  Choosing a project on the PO adds the project's analytic account to PO lines analytic
  distribution.

* Analytic Distribution of storable product in purchase order line follows following rule
  (limited to project's analytic): stored product (`product`) are blocked on company's internal
  project's analytic plan and consummable products (`consu`) are blocked on the PO's project
  analytic plan. Indeed, to value the *Encours de production par affaire*, one need to only value
  the outgoing stock moves per-project and not the incoming ones.

* Adds delivery and invoicing address to project form's *Description* tab,
  selected within customer's addresses by types (delivery, invoicing) or default one

