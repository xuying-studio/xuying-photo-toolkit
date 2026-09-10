#!/usr/bin/env bash
set -euo pipefail

# 构建无界面的 Apple Vision 动态库，供 Python/QML 适配器调用。
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${1:-$ROOT/build/native}"
mkdir -p "$OUTPUT_DIR"

xcrun swiftc \
  -parse-as-library \
  -O \
  -emit-library \
  -module-name XuyingVisionBridge \
  -framework Foundation \
  -framework ImageIO \
  -framework Vision \
  "$ROOT/native/macos_vision/XuyingVisionBridge.swift" \
  -o "$OUTPUT_DIR/libXuyingVision.dylib"

codesign --force --sign - "$OUTPUT_DIR/libXuyingVision.dylib"
echo "$OUTPUT_DIR/libXuyingVision.dylib"
