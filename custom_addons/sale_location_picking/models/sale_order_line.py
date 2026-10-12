from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    delivery_location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Vị trí giao",
        domain="[('usage', 'in', ['internal', 'customer'])]",
        check_company=True,
        help=(
            "Stock destination for this sales line. Leave empty to use the "
            "destination from the standard delivery route."
        ),
    )

    def _prepare_procurement_values(self):
        values = super()._prepare_procurement_values()
        self.ensure_one()
        if self.delivery_location_id:
            # Preserve the recordset here. Odoo serializes BaseModel values
            # when it stores procurement values on the resulting stock move.
            values["location_dest_id"] = self.delivery_location_id.id
        return values
