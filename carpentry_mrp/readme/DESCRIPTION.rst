
=============
Main features
=============


Carpentry Features
******************

produits finis : `move_finished_ids` ?

- article :
    - fonction "référence de remplacement"
    - doc moulinette Orgadata (processus : idem brouillon tableau)
- moulinette Orgadata :
    1. créer l'OF
        choix produit(s) = type d'ouvrage générique (MR, ...)
        choix lancement(s) : nom de l'OF pré-rempli si 1 lancement
        création de lot auto, même N° que l'OF
    2. lecture besoin Orgadata
        a) repère de type 'produits finis' affectés à l'OF
        b) rapport besoin : importé, remplacé, ignoré explicitement, inconnu -> export XLSX
        -> rempli la réservation (composants)
        c) prix des articles et profilés : rempli supplierinfo (avant la résa)
    3. résa du budget
        > Quid correspondance rep produit fini+qty <-> rep budget+qty
- OF multi-produits
    * fiche produit : "peut être fabiqué". Filtre dans les OF [module dédié]
    * qty de l'OF: compute readonly depuis un <notebook/page> 'Produits finis'
    * notebook page 'Produits finis': les champs 'Descr' du 'stock.picking' de 'Stocker les produits finis'
      (synchro stricte. Ajout/Suppression uniquement depuis la vue de l'OF)