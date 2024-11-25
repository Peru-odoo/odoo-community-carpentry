# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _, Command

class Project(models.Model):
    _inherit = 'project.project'

    active = fields.Boolean(
        tracking=True
    )

    # 1 champ date "Début période GPA"
    # Data : 1 plan analytique, 2 axes, en obligatoire
    # 1 méthode '_get_gpa_analaytic_account' : donne l'un des 2 axes selon la date, 'normal' si date pas renseignée
    # bouton "appliquer rétro-activement" qui apparaît sous le <field /> au "onchange"
        # help : "Applique l'axe 'normal' à toutes les dépenses (commandes, factures, sale order, timesheet ? etc...)" avant cette date et l'axe "GPA" après
    
    # models: commandes, factures, sale order, timesheets, ...
    # 1 mixin hérité

    # bouton "clôturer le projet (comptablement)" > 1er stage fold=true
    # bouton "terminer (opérationnellement)" et 'rouvrir' > inactive
