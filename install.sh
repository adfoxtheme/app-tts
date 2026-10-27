#!/usr/bin/env bash
# ==============================================================================
# Script cài đặt: Văn bản thành giọng đọc (Text to Speech - Linux)
# Tác giả: Nguyễn Ngọc Hoan (adfoxtheme)
# Hỗ trợ tự động tất cả các bản phân phối Linux và chạy từ bất kỳ thư mục nào.
# ==============================================================================
set -e

REPO_URL="https://github.com/adfoxtheme/app-tts.git"
TARGET_DIR="$HOME/.local/share/van-ban-thanh-giong-doc"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
TEMP_DIR=""

cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT INT TERM

echo "=========================================================="
echo "    🎙️  CÀI ĐẶT ỨNG DỤNG VĂN BẢN THÀNH GIỌNG ĐỌC          "
echo "=========================================================="

# 1. Xác định thư mục chứa mã nguồn ứng dụng
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]}" ] && [ "${BASH_SOURCE[0]}" != "$0" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

if [ -n "$SCRIPT_DIR" ] && [ -d "$SCRIPT_DIR/app" ] && [ -d "$SCRIPT_DIR/engine" ]; then
    SRC_DIR="$SCRIPT_DIR"
    echo "✓ Sử dụng mã nguồn tại thư mục hiện tại: $SRC_DIR"
else
    echo "⬇️ Đang tải mã nguồn mới nhất từ GitHub ($REPO_URL)..."
    TEMP_DIR="$(mktemp -d /tmp/app-tts-install-XXXXXX)"
    if command -v git &>/dev/null; then
        git clone --depth 1 "$REPO_URL" "$TEMP_DIR" -q
    else
        echo "Đang tải gói lưu trữ qua curl..."
        curl -fsSL "https://github.com/adfoxtheme/app-tts/archive/refs/heads/main.tar.gz" | tar -xz -C "$TEMP_DIR" --strip-components=1
    fi
    SRC_DIR="$TEMP_DIR"
    echo "✓ Đã tải mã nguồn thành công."
fi

# 2. Kiểm tra Python 3
if ! command -v python3 &>/dev/null; then
    echo "❌ Lỗi: Hệ thống chưa cài đặt Python 3!" >&2
    echo "Vui lòng cài đặt python3 bằng trình quản lý gói của OS rồi thử lại." >&2
    exit 1
fi

PYTHON_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "✓ Phiên bản Python phát hiện: $PYTHON_VER"

# 3. Tự động kiểm tra và cài đặt gói giao diện hệ thống cho các OS khác nhau
check_system_dependencies() {
    if python3 -c "import gi; gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1'); gi.require_version('Gst', '1.0'); from gi.repository import Gtk, Adw, Gst" 2>/dev/null; then
        echo "✓ Thư viện hệ thống (GTK4, Libadwaita, GStreamer) đã sẵn sàng."
        return 0
    fi

    echo "⚙️ Đang bổ sung thư viện đồ họa hệ thống (GTK4 / Libadwaita / GStreamer)..."
    
    SUDO_CMD=""
    if [ "$(id -u)" -ne 0 ]; then
        if command -v sudo &>/dev/null; then
            SUDO_CMD="sudo"
        fi
    fi

    if command -v apt-get &>/dev/null; then
        echo "Phát hiện hệ điều hành họ Debian/Ubuntu..."
        $SUDO_CMD apt-get update -qq || true
        $SUDO_CMD apt-get install -y -qq gir1.2-adw-1 gir1.2-gtk-4.0 python3-gi python3-gi-cairo gstreamer1.0-plugins-base gstreamer1.0-plugins-good || true
    elif command -v dnf &>/dev/null; then
        echo "Phát hiện hệ điều hành họ Fedora/RHEL..."
        $SUDO_CMD dnf install -y libadwaita gtk4 python3-gobject gstreamer1-plugins-base gstreamer1-plugins-good || true
    elif command -v pacman &>/dev/null; then
        echo "Phát hiện hệ điều hành họ Arch Linux..."
        $SUDO_CMD pacman -S --needed --noconfirm libadwaita gtk4 python-gobject gst-plugins-base gst-plugins-good || true
    elif command -v zypper &>/dev/null; then
        echo "Phát hiện hệ điều hành openSUSE..."
        $SUDO_CMD zypper install -y typelib-1_0-Adw-1 typelib-1_0-Gtk-4_0 python3-gobject gstreamer-plugins-base gstreamer-plugins-good || true
    elif command -v apk &>/dev/null; then
        echo "Phát hiện hệ điều hành Alpine Linux..."
        $SUDO_CMD apk add libadwaita gtk4.0 py3-gobject gstreamer gst-plugins-base gst-plugins-good || true
    else
        echo "⚠️ Lưu ý: Hãy đảm bảo máy tính đã cài đặt: GTK4, Libadwaita và GStreamer."
    fi
}
check_system_dependencies

# 4. Tạo các thư mục cấu trúc người dùng
mkdir -p "$TARGET_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"

# 5. Sao chép mã nguồn ứng dụng và engine
echo "Đang cài đặt tệp chương trình vào $TARGET_DIR..."
rm -rf "$TARGET_DIR/app" "$TARGET_DIR/engine"
cp -r "$SRC_DIR/app" "$TARGET_DIR/"
cp -r "$SRC_DIR/engine" "$TARGET_DIR/"

# 6. Thiết lập công cụ quản lý gói siêu tốc 'uv'
UV_BIN="$HOME/.local/bin/uv"
if [ ! -f "$UV_BIN" ]; then
    if command -v uv &>/dev/null; then
        UV_BIN="$(command -v uv)"
    else
        echo "Đang cài đặt công cụ quản lý môi trường ảo siêu tốc 'uv'..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        UV_BIN="$HOME/.local/bin/uv"
    fi
fi

# 7. Khởi tạo virtual environment
VENV_DIR="$TARGET_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Đang tạo môi trường Python ảo cách ly độc lập..."
    "$UV_BIN" venv --python /usr/bin/python3 --system-site-packages "$VENV_DIR"
fi

# 8. Cài đặt các thư viện AI (PyTorch CPU, Phonemizer, Audio)
echo "Đang tải và cài đặt các thư viện AI chuyên biệt cho CPU..."
export UV_CACHE_DIR="/tmp/uv-cache-$(id -u)"
mkdir -p "$UV_CACHE_DIR"

"$UV_BIN" pip install --python "$VENV_DIR/bin/python3" -r "$SRC_DIR/requirements.txt"
rm -rf "$UV_CACHE_DIR"

# 9. Áp dụng bản vá tương thích cho vinorm trên Python 3.12+ (nếu có)
find "$VENV_DIR" -type f -name "__init__.py" -path "*/vinorm/*" | while read -r vinorm_file; do
    if grep -q "import imp" "$vinorm_file" 2>/dev/null; then
        echo "Áp dụng bản vá tương thích vinorm..."
        sed -i 's/\r$//' "$vinorm_file"
        sed -i 's/import imp//g' "$vinorm_file"
        sed -i 's/A=imp.find_module.*$/A=os.path.dirname(os.path.abspath(__file__))/g' "$vinorm_file"
    fi
done

# 10. Cài đặt lệnh thực thi Terminal
echo "Đang cấu hình lệnh chạy Terminal..."
cp "$SRC_DIR/bin/van-ban-thanh-giong-doc" "$BIN_DIR/"
chmod +x "$BIN_DIR/van-ban-thanh-giong-doc"

# Thêm ~/.local/bin vào PATH nếu chưa có
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
    for shell_rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
        if [ -f "$shell_rc" ] && ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$shell_rc" 2>/dev/null; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$shell_rc"
        fi
    done
fi

# 11. Cài đặt Biểu tượng (Icon) & Lối tắt Desktop Menu
echo "Đang đăng ký ứng dụng vào Desktop Menu..."
cp "$SRC_DIR/app/assets/icon.svg" "$ICON_DIR/io.github.adfoxtheme.VanBanThanhGiongDoc.svg"
cp "$SRC_DIR/desktop/io.github.adfoxtheme.VanBanThanhGiongDoc.desktop" "$DESKTOP_DIR/"

update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo ""
echo "=========================================================="
echo "  🎉  CÀI ĐẶT THÀNH CÔNG ỨNG DỤNG VĂN BẢN THÀNH GIỌNG ĐỌC! "
echo "=========================================================="
echo "• Mở từ Menu ứng dụng: Tìm kiếm 'Văn bản thành giọng đọc'"
echo "• Mở từ bất kỳ cửa sổ Terminal nào: van-ban-thanh-giong-doc"
echo "=========================================================="
