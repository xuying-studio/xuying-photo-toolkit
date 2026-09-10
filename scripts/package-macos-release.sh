#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="2.0.0-rc.1"
PRODUCT="旭影工具箱"
ASSET_STEM="Xuying-Toolbox-$VERSION-macos-arm64"
DIST_DIR="$ROOT/build/release-dist"
WORK_DIR="$ROOT/build/release-work"
APP="$DIST_DIR/$PRODUCT.app"
RELEASE_DIR="$ROOT/artifacts/releases/$VERSION/macos-arm64"
VALIDATION_REPORT="$ROOT/build/release-validation/macos-arm64.json"
SIGN_IDENTITY="${APPLE_SIGN_IDENTITY:--}"
NOTARY_PROFILE="${NOTARYTOOL_PROFILE:-}"

if [[ -e "$RELEASE_DIR" ]]; then
  echo "发布目录已存在，请先保留或改名后再重新生成：$RELEASE_DIR" >&2
  exit 2
fi

cd "$ROOT"
uv sync --locked --group dev
uv run ruff check src tests
uv run pytest -q
./scripts/build-macos-vision.sh
./scripts/build-macos-visuals.sh
./scripts/build-macos-icon.sh
./scripts/build-macos-ffmpeg.sh
uv run python scripts/collect-release-licenses.py \
  --root "$ROOT" \
  --output "$ROOT/build/release-licenses"
uv run pyinstaller --clean --noconfirm \
  --distpath "$DIST_DIR" \
  --workpath "$WORK_DIR" \
  packaging/macos/release.spec

if [[ "$SIGN_IDENTITY" == "-" ]]; then
  codesign --force --deep --sign - "$APP"
else
  codesign --force --deep --options runtime --timestamp --sign "$SIGN_IDENTITY" "$APP"
fi

if [[ "$SIGN_IDENTITY" != "-" && -n "$NOTARY_PROFILE" ]]; then
  NOTARY_DIR="$(mktemp -d "$ROOT/build/notary.XXXXXX")"
  ditto -c -k --sequesterRsrc --keepParent "$APP" "$NOTARY_DIR/$ASSET_STEM-notary.zip"
  xcrun notarytool submit "$NOTARY_DIR/$ASSET_STEM-notary.zip" \
    --keychain-profile "$NOTARY_PROFILE" \
    --wait
  xcrun stapler staple "$APP"
fi

uv run python scripts/validate-macos-release.py \
  --app "$APP" \
  --report "$VALIDATION_REPORT"

mkdir -p "$RELEASE_DIR/sources" "$RELEASE_DIR/licenses"
ditto "$APP" "$RELEASE_DIR/$PRODUCT.app"
ditto -c -k --sequesterRsrc --keepParent \
  "$APP" \
  "$RELEASE_DIR/$ASSET_STEM.zip"
ditto "$ROOT/build/release-licenses" "$RELEASE_DIR/licenses"
cp "$ROOT/build/downloads/ffmpeg-9.0.1.tar.xz" "$RELEASE_DIR/sources/"
cp "$ROOT/build/downloads/ffmpeg-9.0.1.tar.xz.asc" "$RELEASE_DIR/sources/"
cp "$ROOT/build/ffmpeg/BUILD_CONFIGURATION.txt" "$RELEASE_DIR/sources/FFmpeg-BUILD_CONFIGURATION.txt"
cp "$VALIDATION_REPORT" "$RELEASE_DIR/validation-report.json"

DMG_STAGE="$(mktemp -d "$ROOT/build/dmg-stage.XXXXXX")"
ditto "$APP" "$DMG_STAGE/$PRODUCT.app"
ln -s /Applications "$DMG_STAGE/Applications"
hdiutil create \
  -volname "$PRODUCT $VERSION" \
  -srcfolder "$DMG_STAGE" \
  -format UDZO \
  -imagekey zlib-level=9 \
  "$RELEASE_DIR/$ASSET_STEM.dmg"
if [[ "$SIGN_IDENTITY" != "-" ]]; then
  codesign --force --timestamp --sign "$SIGN_IDENTITY" "$RELEASE_DIR/$ASSET_STEM.dmg"
fi
if [[ "$SIGN_IDENTITY" != "-" && -n "$NOTARY_PROFILE" ]]; then
  xcrun notarytool submit "$RELEASE_DIR/$ASSET_STEM.dmg" \
    --keychain-profile "$NOTARY_PROFILE" \
    --wait
  xcrun stapler staple "$RELEASE_DIR/$ASSET_STEM.dmg"
fi
hdiutil verify "$RELEASE_DIR/$ASSET_STEM.dmg"

uv run python scripts/write-release-manifest.py "$RELEASE_DIR"

echo "Mac 阶段 7 产物已生成：$RELEASE_DIR"
