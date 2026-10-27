#!/usr/bin/env bash
# ==============================================================================
# Script gỡ cài đặt: Văn bản thành giọng đọc (Text to Speech - Linux)
# Tác giả: Nguyễn Ngọc Hoan (adfoxtheme)
# ==============================================================================
set -e

TARGET_DIR="$HOME/.local/share/van-ban-thanh-giong-doc"
BIN_FILE="$HOME/.local/bin/van-ban-thanh-giong-doc"
DESKTOP_FILE="$HOME/.local/share/applications/io.github.adfoxtheme.VanBanThanhGiongDoc.desktop"
ICON_FILE="$HOME/.local/share/icons/hicolor/scalable/apps/io.github.adfoxtheme.VanBanThanhGiongDoc.svg"

echo "=== Gỡ cài đặt Văn bản thành giọng đọc ==="

rm -rf "$TARGET_DIR"
rm -f "$BIN_FILE"
rm -f "$DESKTOP_FILE"
rm -f "$ICON_FILE"

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "✓ Đã gỡ bỏ ứng dụng hoàn toàn khỏi máy tính."
