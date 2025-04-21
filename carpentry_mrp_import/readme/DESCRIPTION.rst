
=============
Main features
=============

**Products price**
All product prices are added in supplier info (in top), before adding the products
to the MO's components so they have the correct pricing in replenishment order.

**Substitution references**
On Product Template form, alternative references may be listed. This is used when
importing components from external database.

**Storable or Consummable products**
Mostly storable products are expected to be found in an external database. Such
products are added in Manufacturing Order's component (as per below logics).

Any non-storable products found in components list of an external database are added
in draft order(s) (i.e. quotation(s)) automatically created at this occasion, per supplier.

**Ignored products**
If an external database contains products archived or configured as not purchasable in Odoo,
they are ignored for Manufacturing Order's components.

**Unknown product codes**
If an external contains products with unknown code, they are also ignored and shown separatly
in import report.
