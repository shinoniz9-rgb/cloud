# Quy Tắc & Hướng Dẫn Dự Án (Project Rules)

## 1. Đồng bộ với Giao Diện Web (`web_server.py`)
- **Bắt buộc**: Mỗi khi hoàn tất chỉnh sửa tính năng, cấu hình, logic điều khiển, nút bấm, ô chọn (combobox/option menu), ô tích (checkbox/switch) hay trạng thái trong `main.py`, **PHẢI luôn kiểm tra và đồng bộ tương ứng sang `web_server.py`**.
- Đảm bảo giao diện Web (HTML/JS), các API endpoint (`/api/status`, `/api/action`, `/api/update_setting`...) và luồng xử lý trên Web luôn phản ánh đúng 100% tính năng mới nhất của GUI phần mềm.

## 2. Đồng bộ Thư mục Đóng Gói (`dist/`)
- Mọi thay đổi về file tài nguyên (hình ảnh trong `assets/`, cấu hình trong `config.json`) phải được sao chép/đồng bộ sang thư mục `dist/`.
- Khi có thay đổi mã nguồn cốt lõi (`main.py`, `web_server.py`), thực hiện build lại file chạy `dist/TS_Origin_Control.exe` (qua `python build_exe.py`) để đảm bảo người dùng chạy file `.exe` luôn có bản cập nhật mới nhất.
