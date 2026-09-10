#!/usr/bin/env bash
set -euo pipefail

# 从同一份 PNG 生成 macOS App Bundle 所需的多尺寸 ICNS。
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$ROOT/qml/Assets/app_icon.png"
OUTPUT="${1:-$ROOT/build/macos/app_icon.icns}"
WORK_DIR="$(mktemp -d "$ROOT/build/app-icon.XXXXXX")"
ICONSET="$WORK_DIR/AppIcon.iconset"

cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

if [[ ! -f "$SOURCE" ]]; then
  echo "找不到应用图标源文件：$SOURCE" >&2
  exit 2
fi

mkdir -p "$ICONSET" "$(dirname "$OUTPUT")"
sips -z 16 16 "$SOURCE" --out "$ICONSET/icon_16x16.png" >/dev/null
sips -z 32 32 "$SOURCE" --out "$ICONSET/icon_16x16@2x.png" >/dev/null
sips -z 32 32 "$SOURCE" --out "$ICONSET/icon_32x32.png" >/dev/null
sips -z 64 64 "$SOURCE" --out "$ICONSET/icon_32x32@2x.png" >/dev/null
sips -z 128 128 "$SOURCE" --out "$ICONSET/icon_128x128.png" >/dev/null
sips -z 256 256 "$SOURCE" --out "$ICONSET/icon_128x128@2x.png" >/dev/null
sips -z 256 256 "$SOURCE" --out "$ICONSET/icon_256x256.png" >/dev/null
sips -z 512 512 "$SOURCE" --out "$ICONSET/icon_256x256@2x.png" >/dev/null
sips -z 512 512 "$SOURCE" --out "$ICONSET/icon_512x512.png" >/dev/null
sips -z 1024 1024 "$SOURCE" --out "$ICONSET/icon_512x512@2x.png" >/dev/null
iconutil -c icns "$ICONSET" -o "$OUTPUT"
echo "$OUTPUT"
