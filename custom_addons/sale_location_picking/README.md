# Module chọn vị trí giao theo dòng bán (Odoo 19)

Module thêm trường **Vị trí giao** trên từng dòng `sale.order.line`. Nếu cùng
một sản phẩm phải giao đến nhiều địa điểm, người dùng thêm nhiều dòng cho sản
phẩm đó và chia số lượng theo từng dòng.

Ví dụ: 10 cái ghế, gồm 6 cái đến A và 4 cái đến B, được nhập thành hai dòng
Ghế: số lượng 6, vị trí A; và số lượng 4, vị trí B.

## Luồng hoạt động

1. Người dùng chọn địa điểm trên dòng sản phẩm của đơn bán.
2. Khi xác nhận đơn, `sale_stock` chuẩn bị dữ liệu procurement cho từng dòng.
3. Module đưa vị trí đã chọn vào dữ liệu procurement.
4. Hook chuẩn `stock.rule._get_custom_move_fields()` chuyển
   `location_dest_id` sang `stock.move` được tạo.
5. Odoo tiếp tục tự tạo move và gán move vào picking theo logic chuẩn. Khi
   đích đến khác nhau, các move được tách thành các picking riêng nếu các giá
   trị gom nhóm còn lại phù hợp.

Module không tự tạo `stock.picking`.

## Giả định và giới hạn

- Loại phiếu vẫn do route bán hàng chuẩn quyết định, thường là **Delivery
  Orders**. Module chỉ đổi vị trí đích của move, không đổi loại phiếu thành
  **Internal Transfer**.
- Trường cho phép chọn vị trí nội bộ hoặc vị trí khách hàng. Nếu chọn vị trí
  nội bộ trong khi loại phiếu là Delivery Orders, cần xác nhận cách vận hành
  này phù hợp với quy trình kho. Đích nội bộ khác với giao hàng cho khách; cần
  rà soát số lượng đã giao và quy tắc lập hóa đơn cho luồng thực tế.
- Nếu để trống vị trí, Odoo dùng đích đến chuẩn của route.
- Với route nhiều bước, module đưa vị trí đã chọn vào move được tạo bởi rule
  tương ứng; cần rà soát toàn bộ chuỗi route nếu hệ thống đang dùng nhiều bước
  nhập/xuất kho.
- Tài khoản người dùng cần quyền đọc `stock.location` để tìm và chọn địa điểm.
- Module chưa được cài trên instance Odoo của bạn. Cần kiểm tra view và luồng
  route trên một database Odoo 19 thử nghiệm trước khi dùng thật.

## Vì sao dùng các hook này?

- `sale.order.line._prepare_procurement_values()` là hook chuẩn để bổ sung dữ
  liệu dòng bán vào procurement khi xác nhận đơn.
- `stock.rule._get_custom_move_fields()` được Odoo cung cấp để chuyển các giá
  trị mở rộng trong procurement sang move mà không phải viết lại toàn bộ hàm
  chuẩn tạo move.
- Odoo vẫn chịu trách nhiệm tạo move và picking, nhờ đó luồng chuẩn về route,
  hủy và giữ hàng tiếp tục được sử dụng.

## Cài đặt

Chép thư mục addon này vào một addons path mà máy chủ Odoo 19 đang đọc, cập
nhật danh sách Apps rồi cài **Sale Delivery Location per Line**.
