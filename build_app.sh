#!/bin/zsh
set -euo pipefail

# 始终从项目目录执行，避免中文路径和空格导致相对路径错误。
project_dir="${0:A:h}"
cd "$project_dir"

app_name="旭影工具箱"
app_path="$project_dir/dist/$app_name.app"
zip_path="$project_dir/dist/$app_name-macOS-arm64.zip"
dmg_path="$project_dir/dist/$app_name-macOS-arm64.dmg"
keyword_source="$project_dir/native/keyword_aligner"
keyword_build="$project_dir/build/keyword_aligner"
keyword_library_name="libKeywordAlignerBridge.dylib"
keyword_library="$keyword_build/arm64-apple-macosx/release/$keyword_library_name"
keyword_framework="$app_path/Contents/Frameworks/$keyword_library_name"
keyword_sdk="${KEYWORD_ALIGNER_SDK:-/Library/Developer/CommandLineTools/SDKs/MacOSX13.3.sdk}"
vibrancy_source="$project_dir/native/macos_vibrancy.m"
vibrancy_library="$project_dir/build/native/libxuying_vibrancy.dylib"
sign_identity="${APPLE_SIGN_IDENTITY:--}"
notary_profile="${APPLE_NOTARY_PROFILE:-}"

archive_previous_release() {
  local info_plist="$app_path/Contents/Info.plist"
  if [[ ! -f "$info_plist" ]]; then
    return
  fi

  local previous_version
  local previous_build
  previous_version="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$info_plist" 2>/dev/null || true)"
  previous_build="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$info_plist" 2>/dev/null || true)"
  if [[ -z "$previous_version" || -z "$previous_build" ]]; then
    return
  fi

  local history_dir="$project_dir/dist/history/v${previous_version}-build${previous_build}"
  local versioned_name="$app_name-v${previous_version}-build${previous_build}"
  mkdir -p "$history_dir"

  # 历史版本只在首次归档时写入，避免后续构建覆盖旧安装包。
  if [[ ! -d "$history_dir/$versioned_name.app" ]]; then
    ditto "$app_path" "$history_dir/$versioned_name.app"
  fi
  if [[ -f "$zip_path" && ! -f "$history_dir/$versioned_name-macOS-arm64.zip" ]]; then
    ditto "$zip_path" "$history_dir/$versioned_name-macOS-arm64.zip"
  fi
  if [[ -f "$dmg_path" && ! -f "$history_dir/$versioned_name-macOS-arm64.dmg" ]]; then
    ditto "$dmg_path" "$history_dir/$versioned_name-macOS-arm64.dmg"
  fi

  echo "已保留历史版本：$history_dir"
}

build_keyword_quickcut() {
  if [[ ! -f "$keyword_source/Package.swift" ]]; then
    echo "未找到关键词快切内嵌源码：$keyword_source" >&2
    exit 1
  fi
  if [[ ! -d "$keyword_sdk" ]]; then
    keyword_sdk="$(xcrun --sdk macosx --show-sdk-path)"
  fi
  mkdir -p "$keyword_build/module-cache" "$keyword_build/clang-cache"
  CLANG_MODULE_CACHE_PATH="$keyword_build/clang-cache" \
  SWIFTPM_MODULECACHE_OVERRIDE="$keyword_build/module-cache" \
    swift build \
      --package-path "$keyword_source" \
      --scratch-path "$keyword_build" \
      --configuration release \
      --product KeywordAlignerBridge \
      --arch arm64 \
      --sdk "$keyword_sdk" \
      --disable-sandbox \
      --disable-build-manifest-caching
  if [[ ! -f "$keyword_library" ]]; then
    echo "关键词快切桥接构建失败：$keyword_library" >&2
    exit 1
  fi
}

install_keyword_quickcut() {
  mkdir -p "${keyword_framework:h}"
  cp "$keyword_library" "$keyword_framework"
  install_name_tool -id "@rpath/$keyword_library_name" "$keyword_framework"
}

sign_bundle() {
  local bundle_path="$1"
  if [[ "$sign_identity" == "-" ]]; then
    codesign --force --deep --sign - "$bundle_path"
  else
    codesign \
      --force \
      --deep \
      --options runtime \
      --timestamp \
      --sign "$sign_identity" \
      "$bundle_path"
  fi
}

build_native_vibrancy() {
  mkdir -p "${vibrancy_library:h}"
  clang \
    -dynamiclib \
    -fobjc-arc \
    -framework Cocoa \
    -arch arm64 \
    -mmacosx-version-min=13.0 \
    "$vibrancy_source" \
    -o "$vibrancy_library"
  [[ "$(lipo -archs "$vibrancy_library")" == "arm64" ]]
}

build_keyword_quickcut
build_native_vibrancy
python3 -m unittest discover -s tests -v
archive_previous_release
python3 -m PyInstaller --clean --noconfirm photo_assistant.spec
install_keyword_quickcut
sign_bundle "$keyword_framework"
codesign --verify --strict --verbose=2 "$keyword_framework"
sign_bundle "$app_path"

codesign --verify --deep --strict --verbose=2 "$app_path"

rm -f "$zip_path"
ditto -c -k --sequesterRsrc --keepParent "$app_path" "$zip_path"

if [[ -n "$notary_profile" && "$sign_identity" != "-" ]]; then
  xcrun notarytool submit "$zip_path" --keychain-profile "$notary_profile" --wait
  xcrun stapler staple "$app_path"
  rm -f "$zip_path"
  ditto -c -k --sequesterRsrc --keepParent "$app_path" "$zip_path"
fi

dmg_stage="$(mktemp -d "${TMPDIR:-/tmp}/photo-assistant-dmg.XXXXXX")"
trap 'rm -rf "$dmg_stage"' EXIT
ditto "$app_path" "$dmg_stage/$app_name.app"
ln -s /Applications "$dmg_stage/Applications"
rm -f "$dmg_path"
hdiutil create \
  -volname "$app_name" \
  -srcfolder "$dmg_stage" \
  -ov \
  -format UDZO \
  "$dmg_path"

echo "App：$app_path"
echo "分发包：$zip_path"
echo "安装镜像：$dmg_path"
