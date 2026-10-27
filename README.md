# 🎙️ Văn bản thành giọng đọc (App TTS Linux)

Ứng dụng chuyển đổi văn bản thành giọng nói (Text-to-Speech) chuẩn giao diện **GNOME / Linux (GTK 4 & Libadwaita)**, tích hợp mô hình trí tuệ nhân tạo **V-TTS** siêu nhẹ chạy trực tiếp trên vi xử lý CPU mà không cần card đồ họa rời (GPU).

---

## ✨ Tính năng nổi bật

* **Giao diện chuẩn GNOME / Libadwaita**:
  * Thiết kế hiện đại, bo góc mềm mại, tự động đồng bộ theo giao diện Sáng / Tối (Light / Dark mode) của hệ thống.
  * Bố cục 2 cột trực quan: Khung soạn thảo văn bản bên trái và Bảng điều khiển giọng đọc cùng trình phát bên phải.
* **Đa dạng giọng đọc tiếng Việt (Preset Voices)**:
  * 👩 **Nữ miền Bắc (Hà Nội - `NF`)**: Thanh lịch, chuẩn ngữ điệu thủ đô.
  * 👩 **Nữ miền Nam (Sài Gòn - `SF`)**: Ngọt ngào, truyền cảm và tự nhiên.
  * 👨 **Nam miền Bắc 1 (Hà Nội - `NM1`)**: Trầm ấm, chững chạc và trang trọng.
  * 👨 **Nam miền Bắc 2 (Hà Nội - `NM2`)**: Trẻ trung, tươi sáng và năng động.
  * 👨 **Nam miền Nam (Sài Gòn - `SM`)**: Rõ ràng, phóng khoáng và hiện đại.
* **Nhân bản giọng nói AI (Zero-Shot Voice Cloning)**:
  * Cho phép tải lên một file âm thanh mẫu ngắn (3–10 giây `.wav`, `.mp3`) để AI trích xuất đặc trưng âm học và mô phỏng giọng đọc tương tự.
* **Xử lý văn bản & Phụ đề thông minh**:
  * Mở nhanh file văn bản (`.txt`) hoặc file phụ đề phim (`.srt` - tự động lọc sạch các mốc thời gian timestamp).
  * Bộ đếm thời gian thực: số ký tự, số từ và ước lượng thời lượng đọc tương ứng.
  * Chế độ **Ngắt nghỉ tự nhiên**: Tự động phân tách từng câu văn và ngắt nghỉ tự nhiên theo dấu câu.
* **Trình phát âm thanh tích hợp (Audio Player)**:
  * Phát trực tiếp âm thanh qua hệ thống PipeWire / GStreamer của Linux.
  * Thanh tua thời gian (Seekbar), nút tua tiến/lùi 5 giây và nút xuất file âm thanh lossless (`.wav`).

---

## 🛠️ Yêu cầu hệ thống

* **Hệ điều hành**: Linux (Ubuntu 22.04+, Debian 12+, Fedora 38+, Arch Linux,...).
* **Môi trường đồ họa**: GNOME hoặc bất kỳ Desktop Environment nào hỗ trợ GTK4 / Libadwaita.
* **Phần cứng**: Vi xử lý CPU tiêu chuẩn (không bắt buộc có card GPU rời).
* **Python**: Python 3.10 trở lên cùng các gói GObject Introspection (`gir1.2-gtk-4.0`, `gir1.2-adw-1`, `python3-gi`).

---

## 🚀 Hướng dẫn cài đặt

Mở Terminal và chạy các lệnh sau:

```bash
# 1. Clone repository về máy
git clone https://github.com/adfoxtheme/app-tts.git
cd app-tts

# 2. Cấp quyền thực thi và chạy script cài đặt
chmod +x install.sh
./install.sh
```

Quá trình cài đặt sẽ:
1. Sao chép chương trình vào thư mục người dùng: `~/.local/share/van-ban-thanh-giong-doc/`
2. Thiết lập môi trường Python ảo cách ly độc lập (không làm ảnh hưởng tới hệ điều hành).
3. Đăng ký phím tắt trong danh mục ứng dụng của Linux (`io.github.adfoxtheme.VanBanThanhGiongDoc.desktop`) cùng bộ biểu tượng vector sắc nét.

---

## 💻 Cách sử dụng

* **Từ Menu ứng dụng**: Nhấn phím `Super` (phím Windows), tìm kiếm **"Văn bản thành giọng đọc"** và nhấp để mở.
* **Từ Terminal**:
  ```bash
  van-ban-thanh-giong-doc
  ```

---

## 🗑️ Gỡ cài đặt

Nếu bạn muốn gỡ bỏ hoàn toàn ứng dụng khỏi hệ thống, chạy lệnh:

```bash
cd app-tts
chmod +x uninstall.sh
./uninstall.sh
```

---

## 📜 Giấy phép & Ghi công

* **Tác giả ứng dụng**: [Nguyễn Ngọc Hoan (adfoxtheme)](https://github.com/adfoxtheme)
* **Bộ máy AI TTS**: Dựa trên mô hình mã nguồn mở [v-tts](https://github.com/tronghieuit/v-tts) của tác giả **Lê Trọng Hiếu (tronghieuit)**.
* **Giấy phép**: Phát hành theo giấy phép [MIT License](LICENSE).
