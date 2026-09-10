#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="9.0.1"
SHA256="cf38e0e28c7e5605942c4a77755349b0145804a397af37eb1fb4c77cb237f635"
DOWNLOAD_DIR="$ROOT/build/downloads"
ARCHIVE="$DOWNLOAD_DIR/ffmpeg-$VERSION.tar.xz"
SIGNATURE="$ARCHIVE.asc"
SOURCE_DIR="$ROOT/build/ffmpeg-source/ffmpeg-$VERSION"
OUTPUT_DIR="$ROOT/build/ffmpeg"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "此脚本只构建 macOS arm64 FFmpeg。" >&2
  exit 2
fi

mkdir -p "$DOWNLOAD_DIR" "$ROOT/build/ffmpeg-source" "$OUTPUT_DIR/bin"
if [[ ! -f "$ARCHIVE" ]]; then
  curl -fL --retry 5 -o "$ARCHIVE" "https://ffmpeg.org/releases/ffmpeg-$VERSION.tar.xz"
fi
if [[ ! -f "$SIGNATURE" ]]; then
  curl -fL --retry 5 -o "$SIGNATURE" "https://ffmpeg.org/releases/ffmpeg-$VERSION.tar.xz.asc"
fi

echo "$SHA256  $ARCHIVE" | shasum -a 256 -c -
xz -t "$ARCHIVE"
if [[ ! -d "$SOURCE_DIR" ]]; then
  tar -xf "$ARCHIVE" -C "$ROOT/build/ffmpeg-source"
fi

cd "$SOURCE_DIR"
./configure \
  --arch=arm64 \
  --target-os=darwin \
  --cc=clang \
  --enable-zlib \
  --disable-debug \
  --disable-doc \
  --disable-network \
  --disable-ffplay \
  --disable-ffprobe \
  --disable-avdevice \
  --disable-swresample \
  --disable-iconv \
  --disable-bzlib \
  --disable-lzma \
  --disable-sdl2 \
  --disable-audiotoolbox \
  --disable-securetransport \
  --disable-encoders \
  --disable-decoders \
  --disable-demuxers \
  --disable-muxers \
  --disable-parsers \
  --disable-protocols \
  --disable-bsfs \
  --disable-filters \
  --disable-hwaccels \
  --disable-indevs \
  --disable-outdevs \
  --enable-encoder=h264_videotoolbox \
  --enable-decoder=png \
  --enable-parser=png \
  --enable-demuxer=image2 \
  --enable-muxer=mp4 \
  --enable-protocol=file \
  --enable-filter=format \
  --enable-filter=scale \
  --extra-cflags="-mmacosx-version-min=13.0" \
  --extra-ldflags="-mmacosx-version-min=13.0"
make -j"$(sysctl -n hw.logicalcpu)" ffmpeg
install -m 755 ffmpeg "$OUTPUT_DIR/bin/ffmpeg"
"$OUTPUT_DIR/bin/ffmpeg" -version > "$OUTPUT_DIR/BUILD_CONFIGURATION.txt"

if ! "$OUTPUT_DIR/bin/ffmpeg" -hide_banner -encoders 2>&1 | grep -q h264_videotoolbox; then
  echo "FFmpeg 缺少 h264_videotoolbox 编码器。" >&2
  exit 3
fi
if otool -L "$OUTPUT_DIR/bin/ffmpeg" | grep -Eq '/opt/homebrew|/usr/local'; then
  echo "FFmpeg 意外链接到本机 Homebrew 依赖。" >&2
  exit 4
fi
