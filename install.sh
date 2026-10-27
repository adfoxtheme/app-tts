#!/usr/bin/env bash
# ==============================================================================
# Script cài đặt: Văn bản thành giọng đọc (Text to Speech - Linux)
# Tác giả: Nguyễn Ngọc Hoan (adfoxtheme)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.local/share/van-ban-thanh-giong-doc"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

echo "=== Cài đặt Văn bản thành giọng đọc ==="

# 1. Kiểm tra Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Lỗi: Chưa cài đặt python3 trên hệ thống!" >&2
    exit 1
fi

PYTHON_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "✓ Phát hiện Python: $PYTHON_VER"

# 2. Tạo các thư mục đích
mkdir -p "$TARGET_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"

# 3. Sao chép mã nguồn ứng dụng và engine
echo "Đang sao chép tệp chương trình vào $TARGET_DIR..."
rm -rf "$TARGET_DIR/app" "$TARGET_DIR/engine"
cp -r "$SCRIPT_DIR/app" "$TARGET_DIR/"
cp -r "$SCRIPT_DIR/engine" "$TARGET_DIR/"

# 4. Thiết lập môi trường Python ảo (venv)
VENV_DIR="$TARGET_DIR/venv"
UV_BIN="$HOME/.local/bin/uv"

if [ ! -f "$UV_BIN" ]; then
    if command -v uv &>/dev/null; then
        UV_BIN="$(command -v uv)"
    else
        echo "Đang cài đặt công cụ quản lý gói siêu nhanh 'uv'..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        UV_BIN="$HOME/.local/bin/uv"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Đang khởi tạo môi trường Python ảo..."
    "$UV_BIN" venv --python /usr/bin/python3 --system-site-packages "$VENV_DIR"
fi

# 5. Cài đặt các gói phụ thuộc
echo "Đang cài đặt các thư viện cần thiết (PyTorch CPU, xử lý ngôn ngữ)..."
export UV_CACHE_DIR="/tmp/uv-cache-$(id -u)"
mkdir -p "$UV_CACHE_DIR"

"$UV_BIN" pip install --python "$VENV_DIR/bin/python3" -r "$SCRIPT_DIR/requirements.txt"
rm -rf "$UV_CACHE_DIR"

# 6. Vá lỗi tương thích vinorm trên Python 3.12+ (nếu có)
VINORM_INIT="$VENV_DIR/lib/python$PYTHON_VER/site-packages/vinorm/__init__.py"
if [ -f "$VINORM_INIT" ] && grep -q "import imp" "$VINORM_INIT" 2>/dev/null; then
    echo "Đang áp dụng bản vá tương thích cho vinorm..."
    sed -i 's/\r$//' "$VINORM_INIT"
    sed -i 's/import imp//g' "$VINORM_INIT"
    sed -i 's/A=imp.find_module.*$/A=os.path.dirname(os.path.abspath(__file__))/g' "$VINORM_INIT"
fi

# 7. Cài đặt Launcher thực thi
echo "Đang tạo lệnh gọi terminal..."
cp "$SCRIPT_DIR/bin/van-ban-thanh-giong-doc" "$BIN_DIR/"
chmod +x "$BIN_DIR/van-ban-thanh-giong-doc"

# 8. Cài đặt Icon & Desktop Entry
echo "Đang tạo biểu tượng và lối tắt ứng dụng..."
cp "$SCRIPT_DIR/app/assets/icon.svg" "$ICON_DIR/io.github.adfoxtheme.VanBanThanhGiongDoc.svg"
cp "$SCRIPT_DIR/desktop/io.github.adfoxtheme.VanBanThanhGiongDoc.desktop" "$DESKTOP_DIR/"

update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo ""
echo "🎉 Cài đặt hoàn tất thành công!"
echo "• Khởi chạy từ Menu ứng dụng: Tìm 'Văn bản thành giọng đọc'"
echo "• Khởi chạy từ Terminal: van-ban-thanh-giong-doc"
