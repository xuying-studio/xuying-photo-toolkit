#!/usr/bin/env bash
set -euo pipefail

# 构建只负责原生背景和辅助功能读取的轻量动态库。
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${1:-$ROOT/build/native}"
mkdir -p "$OUTPUT_DIR"

xcrun swiftc \
  -swift-version 5 \
  -parse-as-library \
  -O \
  -emit-library \
  -module-name XuyingMacVisuals \
  -framework AppKit \
  "$ROOT/native/macos_visuals/XuyingMacVisuals.swift" \
  -o "$OUTPUT_DIR/libXuyingMacVisuals.dylib"

codesign --force --sign - "$OUTPUT_DIR/libXuyingMacVisuals.dylib"
echo "$OUTPUT_DIR/libXuyingMacVisuals.dylib"
