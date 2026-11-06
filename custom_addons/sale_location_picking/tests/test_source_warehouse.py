from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestSourceWarehouse(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.wh1 = cls.env["stock.warehouse"].search([("company_id", "=", cls.company.id)], limit=1)
        cls.wh2 = cls.env["stock.warehouse"].create({"name": "Test WH Two", "code": "TW2"})
        cls.product = cls.env["product.product"].create({
            "name": "Test Chair", "is_storable": True, "type": "consu",
        })
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})
        for wh, qty in ((cls.wh1, 100), (cls.wh2, 3)):
            cls.env["stock.quant"]._update_available_quantity(cls.product, wh.lot_stock_id, qty)

    def _order(self, lines):
        return self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "warehouse_id": self.wh1.id,
            "order_line": [(0, 0, {
                "product_id": self.product.id, "product_uom_qty": qty,
                "source_warehouse_id": wh.id if wh else False,
            }) for qty, wh in lines],
        })

    def test_1_default_warehouse(self):
        so = self._order([(5, False)])
        so.action_confirm()
        self.assertEqual(so.order_line.warehouse_id, self.wh1)
        self.assertEqual(so.picking_ids.move_ids.location_id, self.wh1.lot_stock_id)
        self.assertEqual(so.picking_ids.move_ids.location_dest_id.usage, "customer")

    def test_2_two_warehouses(self):
        so = self._order([(6, self.wh1), (4, self.wh2)])
        so.action_confirm()
        moves = so.picking_ids.move_ids
        self.assertEqual(len(moves), 2)
        self.assertEqual(len(so.picking_ids), 2)
        for line, wh in zip(so.order_line, (self.wh1, self.wh2)):
            move = line.move_ids
            self.assertEqual(len(move), 1)
            self.assertEqual(move.location_id, wh.lot_stock_id)
            self.assertEqual(move.picking_type_id, wh.out_type_id)
            self.assertEqual(move.product_uom_qty, line.product_uom_qty)
            self.assertEqual(move.sale_line_id, line)
            self.assertEqual(move.location_dest_id.usage, "customer")
        self.assertEqual(len(so.picking_ids.mapped("picking_type_id")), 2)

    def test_3_same_warehouse_standard_grouping(self):
        so = self._order([(2, self.wh2), (1, self.wh2)])
        so.action_confirm()
        self.assertEqual(len(so.picking_ids.move_ids), 2)
        self.assertEqual(so.picking_ids.move_ids.location_id, self.wh2.lot_stock_id)
        self.assertEqual(so.picking_ids.picking_type_id, self.wh2.out_type_id)

    def test_4_shortage_reservation(self):
        so = self._order([(10, self.wh2)])  # only 3 available
        so.action_confirm()
        move = so.order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.product_uom_qty, 10)
        self.assertEqual(move.quantity, 3)
        self.assertIn(move.state, ("partially_available", "confirmed"))

    def test_5_block_change_after_confirm(self):
        so = self._order([(2, self.wh1)])
        so.order_line.source_warehouse_id = self.wh2  # allowed in draft
        so.action_confirm()
        with self.assertRaises(UserError):
            so.order_line.source_warehouse_id = self.wh1
        with self.assertRaises(UserError):
            so.order_line.source_warehouse_id = False

    def test_6_invalid_warehouse(self):
        other = self.env["res.company"].create({"name": "Other Co"})
        wh_other = self.env["stock.warehouse"].search([("company_id", "=", other.id)], limit=1)
        with self.assertRaises(Exception):
            self._order([(1, wh_other)])
        # warehouse without delivery route -> clear error at confirm
        self.wh2.delivery_route_id = False
        so = self._order([(1, self.wh2)])
        with self.assertRaises(UserError):
            so.action_confirm()

    def test_7_delivery_done_qty_delivered(self):
        so = self._order([(6, self.wh1), (4, self.wh2)])
        so.action_confirm()
        picking = so.picking_ids.filtered(lambda p: p.picking_type_id == self.wh1.out_type_id)
        picking.move_ids.picked = True
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertEqual(so.order_line[0].qty_delivered, 6)
        self.assertEqual(so.order_line[1].qty_delivered, 0)

    def test_8_reconfirm_no_duplicates(self):
        so = self._order([(6, self.wh1), (4, self.wh2)])
        so.action_confirm()
        count = len(so.order_line.move_ids)
        so.order_line._action_launch_stock_rule()
        with self.assertRaises(UserError):  # standard: cannot confirm twice
            so.action_confirm()
        self.assertEqual(len(so.order_line.move_ids), count)
        so.order_line[0].product_uom_qty = 8  # standard: adds only delta
        self.assertEqual(sum(so.order_line[0].move_ids.mapped("product_uom_qty")), 8)

    def test_9_legacy_dest_off_by_default(self):
        loc = self.env["stock.location"].create({"name": "X", "usage": "internal"})
        so = self._order([(1, self.wh1)])
        so.order_line.delivery_location_id = loc
        so.action_confirm()
        self.assertEqual(so.order_line.move_ids.location_dest_id.usage, "customer")
