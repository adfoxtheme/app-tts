# 🎙️ Văn bản thành giọng đọc (App TTS Linux)

Ứng dụng chuyển đổi văn bản thành giọng nói (Text-to-Speech) chuẩn giao diện **GNOME / Linux (GTK 4 & Libadwaita)**, tích hợp mô hình trí tuệ nhân tạo **V-TTS** siêu nhẹ chạy trực tiếp trên vi xử lý CPU mà không cần card đồ họa rời (GPU).

---

## ⚡ Cài đặt nhanh bằng 1 lệnh duy nhất (Mọi hệ điều hành Linux)

Mở Terminal ở **bất kỳ thư mục nào** và dán lệnh sau để cài đặt tự động:

```bash
curl -fsSL https://raw.githubusercontent.com/adfoxtheme/app-tts/main/install.sh | bash
```

> Hoặc dùng `bash -c`:
> ```bash
> bash -c "$(curl -fsSL https://raw.githubusercontent.com/adfoxtheme/app-tts/main/install.sh)"
> ```

Script sẽ tự động:
1. Nhận diện hệ điều hành (Ubuntu, Debian, Fedora, Arch Linux, openSUSE, Alpine,...) và đảm bảo đủ thư viện đồ họa hệ thống (GTK4, Libadwaita, GStreamer).
2. Tạo môi trường Python ảo độc lập trong thư mục người dùng (`~/.local/share/van-ban-thanh-giong-doc`).
3. Tải và cài đặt các thư viện AI chuyên biệt cho vi xử lý CPU (nhanh, nhẹ, không tốn tài nguyên).
4. Đăng ký lệnh `van-ban-thanh-giong-doc` vào Terminal và thêm ứng dụng vào Desktop Menu với biểu tượng vector sắc nét.

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

## 💻 Cách sử dụng

* **Từ Menu ứng dụng**: Nhấn phím `Super` (phím Windows), tìm kiếm **"Văn bản thành giọng đọc"** và nhấp để mở.
* **Từ Terminal**:
  ```bash
  van-ban-thanh-giong-doc
  ```

---

## 🛠️ Cài đặt thủ công (Dành cho nhà phát triển)

Nếu bạn đã clone repository về máy:

```bash
git clone https://github.com/adfoxtheme/app-tts.git
cd app-tts
chmod +x install.sh
./install.sh
```

---

## 🗑️ Gỡ cài đặt

Chạy 1 lệnh duy nhất để gỡ sạch ứng dụng khỏi hệ thống:

```bash
curl -fsSL https://raw.githubusercontent.com/adfoxtheme/app-tts/main/uninstall.sh | bash
```

---

## 📜 Giấy phép & Ghi công

* **Tác giả ứng dụng**: [Nguyễn Ngọc Hoan (adfoxtheme)](https://github.com/adfoxtheme)
* **Bộ máy AI TTS**: Dựa trên mô hình mã nguồn mở [v-tts](https://github.com/tronghieuit/v-tts) của tác giả **Lê Trọng Hiếu (tronghieuit)**.
* **Giấy phép**: Phát hành theo giấy phép [MIT License](LICENSE).
