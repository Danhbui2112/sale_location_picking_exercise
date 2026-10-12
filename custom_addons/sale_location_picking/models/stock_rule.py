from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _get_custom_move_fields(self):
        fields_to_copy = super()._get_custom_move_fields()
        return fields_to_copy + ["location_dest_id"]
