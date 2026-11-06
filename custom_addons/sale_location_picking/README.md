# Sale Source Warehouse per Line (Odoo 19)

Thêm **Source Warehouse** (`source_warehouse_id`) trên từng `sale.order.line`.

## Luồng
1. User chọn kho nguồn trên dòng (trống = kho của đơn).
2. `_compute_warehouse_id` (chuẩn của `sale_stock`) được mở rộng: sau `super()`, nếu có `source_warehouse_id` thì `warehouse_id` = kho đó.
3. Khi Confirm, `_prepare_procurement_values()` chuẩn đưa `warehouse_id` + `route_ids` vào procurement.
4. `stock.rule.run` → `_get_rule` chọn rule trong route của đúng kho đó (picking type, source location, dest = Customer).
5. `stock.move` / `stock.picking` do Odoo chuẩn tạo và gom nhóm; module không tạo/sửa move hay picking.

## Bảo vệ
- Constraint: kho cùng company; nếu route trên dòng kéo từ kho khác thì ValidationError.
- `write()` chặn đổi kho khi dòng không còn draft/sent.
- Kho không có delivery route thì UserError khi Confirm.

## Chế độ legacy (mặc định TẮT)
`delivery_location_id` chỉ ghi đè `location_dest_id` khi system parameter `sale_location_picking.use_delivery_location` = `True`. Không dùng cho giao khách hàng.

## Lệnh
    odoo-bin -c config/odoo.conf -d <DB> -u sale_location_picking
    odoo-bin -c config/odoo.conf -d <DB_TEST> -u sale_location_picking --test-tags /sale_location_picking --stop-after-init

## Demo UI
Có 2 kho (HCM, HN) với tồn kho. Sales > tạo đơn: dòng Ghế x6 Source Warehouse = HCM; dòng Ghế x4 Source Warehouse = HN > Confirm > smart button Delivery: 2 phiếu Delivery Orders, mỗi phiếu xuất từ `<WH>/Stock` đến Customers.
