# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'project.default.mixin']
    _rec_name = 'display_name'

    #====== Fields' methods ======#
    def name_get(self):
        """ Force to follow `_compute_display_name`
            required because of `section_ref` field in `carpentry.budget.remaining`
        """
        if not self._context.get('display_description'):
            return super().name_get()
        
        return [
            (po.id, "[{}] {}" . format(po.name, po.description))
            for po in self
        ]

    #====== Fields ======#
    project_id = fields.Many2one(
        # not reqiured because of replenishment (stock.warehouse.orderpoint)
        required=False
    )
    description = fields.Char(
        string='Description'
    )
    launch_ids = fields.Many2many(
        comodel_name='carpentry.group.launch',
        relation='purchase_order_launch_rel',
        string='Launches',
        domain="[('project_id', '=', project_id)]",
    )
    needs_count = fields.Integer(
        compute='_compute_needs_count'
    )
    # -- ui --
    products_type = fields.Selection(
        selection=[
            ('none', 'No products'),
            ('storable', 'Stock purchase order (only)'),
            ('non_storable', 'Purchase Order with non-stored products (only)'),
            ('mix', 'Purchase order mixing both stored and non-stored products')
        ],
        compute='_compute_products_type'
    )
    
    #===== Compute =====#
    def _compute_display_name(self):
        for mo in self:
            mo.display_name = '[{}] {}' . format(mo.name, mo.description) if mo.description else mo.name

    @api.depends('launch_ids')
    def _compute_needs_count(self):
        """ Count number of needs, for Magic Button """
        for task in self:
            task.needs_count = len(task.launch_ids.task_ids.filtered(lambda x: not x.is_closed))

    # See purchase_stock/models/purchase.py
    @api.depends('project_id')
    def _compute_dest_address_id(self):
        """ Pre-fill `dest_address_id` when delivered to customer """
        po_to_customer = self.filtered(lambda po: po.picking_type_id.default_location_dest_id.usage == 'customer')
        super(PurchaseOrder, self - po_to_customer)._compute_dest_address_id()

        for po in po_to_customer:
            po.dest_address_id = po.project_id.delivery_address_id
    
    #====== Compute ======#
    @api.depends('order_line', 'order_line.product_id', 'order_line.product_id.type')
    def _compute_products_type(self):
        """ Display a warning if purchase has both storable and consummable products """
        for purchase in self:
            types = set(purchase.order_line.product_id.mapped('type'))
            if 'product' in types and len(types) > 1:
                type = 'mix'
            elif types == {'product'}:
                type = 'storable'
            elif types:
                type = 'non_storable'
            else:
                type = 'none'
            purchase.products_type = type
    
    @api.onchange('project_id', 'partner_id')
    def _onchange_default_requisition(self):
        """ Auto-select Purchase Requisition by project and vendor """
        rg_result = self.env['purchase.requisition'].read_group(
            domain=[('project_id', 'in', self.project_id.ids), ('vendor_id', 'in', self.partner_id.commercial_partner_id.ids)],
            groupby=['project_id', 'vendor_id'],
            fields=['ids:array_agg(id)'],
            lazy=False,
        )
        mapped_data = {
            (x['project_id'][0], x['vendor_id'][0]): x['ids']
            for x in rg_result
        }
        print('mapped_data', mapped_data)
        for purchase in self:
            key = (purchase.project_id.id, purchase.partner_id.commercial_partner_id.id)
            purchase.requisition_id = mapped_data.get(key, [False])[-1]

    # --- project_id (shortcut to set line analytic at once on the project) ---
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """ Modify all lines analytic at once """
        project_analytics = self.env.company.analytic_plan_id.account_ids
        for purchase in self:
            purchase._ensure_project_launches_consistency()
            project_account_id = purchase.project_id._origin.analytic_account_id.id
            purchase.order_line._replace_analytic(
                replaced_ids=project_analytics._origin.ids,
                new_distrib={project_account_id: 100} if project_account_id else {},
                analytic_plan='project',
            )
    
    def _ensure_project_launches_consistency(self):
        """ Launch_ids must belong to the project
            (a discrepency could happen since `project_id` can be modified)
        """
        self.ensure_one()
        to_clean = self.launch_ids.filtered(lambda x: x not in self.project_id.launch_ids)
        if to_clean:
            self.launch_ids -= to_clean
    
    #===== Logics =====#
    def _prepare_picking(self):
        """ Write project from PO to procurement group and picking """
        return super()._prepare_picking() | {
            'project_id': self.project_id.id
        }

    def _prepare_invoice(self):
        """ Write project from PO to invoice """
        return super()._prepare_invoice() | {
            'project_id': self.project_id.id
        }

    #===== Planning =====#
    def _get_planning_domain(self):
        return [('state', '!=', 'draft')]

    #===== Button =====#
    def open_need_kanban(self):
        """ Open Tasks of type Needs related to the PO in kanban view """
        return self.env['project.task'].open_need_kanban(
            launchs=self.launch_ids
        )
