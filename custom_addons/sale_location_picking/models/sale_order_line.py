from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

USE_DELIVERY_LOCATION_PARAM = "sale_location_picking.use_delivery_location"


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    source_warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Source Warehouse",
        check_company=True,
        index="btree_not_null",
        copy=True,
        help=(
            "Warehouse this line is delivered from. Leave empty to use the "
            "warehouse of the sales order. Standard routes and stock rules of "
            "this warehouse select the picking type and source location."
        ),
    )

    # Legacy feature (independent mode, disabled by default).
    delivery_location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Vị trí giao",
        domain="[('usage', 'in', ['internal', 'customer'])]",
        check_company=True,
        help=(
            "LEGACY. Only applied when the system parameter "
            "'sale_location_picking.use_delivery_location' is set to True. "
            "It overrides the destination of the stock move, so it must not be "
            "used for standard delivery to customers."
        ),
    )

    # ------------------------------------------------------------------
    # Warehouse computation: plug the selected warehouse into the standard
    # compute instead of writing the computed field directly.
    # ------------------------------------------------------------------
    @api.depends("source_warehouse_id")
    def _compute_warehouse_id(self):
        super()._compute_warehouse_id()
        for line in self:
            if line.source_warehouse_id:
                line.warehouse_id = line.source_warehouse_id

    @api.constrains("source_warehouse_id", "route_ids", "warehouse_id")
    def _check_source_warehouse_consistency(self):
        for line in self:
            wh = line.source_warehouse_id
            if not wh:
                continue
            if wh.company_id != line.company_id:
                raise ValidationError(_(
                    "Warehouse %(wh)s belongs to another company than the sales order.",
                    wh=wh.display_name,
                ))
            if line.warehouse_id != wh:
                raise ValidationError(_(
                    "The routes selected on line '%(line)s' pull from warehouse "
                    "%(route_wh)s, which conflicts with the Source Warehouse %(wh)s. "
                    "Remove the route or choose a consistent warehouse.",
                    line=line.display_name,
                    route_wh=line.warehouse_id.display_name,
                    wh=wh.display_name,
                ))

    # ------------------------------------------------------------------
    # ORM protection after confirmation
    # ------------------------------------------------------------------
    def write(self, vals):
        if "source_warehouse_id" in vals:
            for line in self:
                if line.state not in ("draft", "sent") and (
                    line.source_warehouse_id.id != (vals["source_warehouse_id"] or False)
                ):
                    raise UserError(_(
                        "You cannot change the Source Warehouse of line '%(line)s' "
                        "once the order is confirmed. Cancel the delivery or add a new line.",
                        line=line.display_name,
                    ))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Procurement
    # ------------------------------------------------------------------
    def _action_launch_stock_rule(self, *, previous_product_uom_qty=False):
        for line in self:
            wh = line.source_warehouse_id
            if (
                wh and line.state == "sale" and line.product_id.type == "consu"
                and not line.route_ids and not wh.delivery_route_id
            ):
                raise UserError(_(
                    "Warehouse %(wh)s has no delivery route configured; cannot deliver "
                    "line '%(line)s' from it.",
                    wh=wh.display_name, line=line.display_name,
                ))
        return super()._action_launch_stock_rule(previous_product_uom_qty=previous_product_uom_qty)

    def _prepare_procurement_values(self):
        values = super()._prepare_procurement_values()
        self.ensure_one()
        use_legacy = self.env["ir.config_parameter"].sudo().get_param(USE_DELIVERY_LOCATION_PARAM)
        if self.delivery_location_id and use_legacy in ("True", "true", "1"):
            values["location_dest_id"] = self.delivery_location_id.id
        return values
