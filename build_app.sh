#!/bin/zsh
set -euo pipefail

# 始终从项目目录执行，避免中文路径和空格导致相对路径错误。
project_dir="${0:A:h}"
cd "$project_dir"

app_name="旭影的摄影工具集"
app_path="$project_dir/dist/$app_name.app"
zip_path="$project_dir/dist/$app_name-macOS-universal.zip"
dmg_path="$project_dir/dist/$app_name-macOS-universal.dmg"
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
  if [[ -f "$zip_path" && ! -f "$history_dir/$versioned_name-macOS-universal.zip" ]]; then
    ditto "$zip_path" "$history_dir/$versioned_name-macOS-universal.zip"
  fi
  if [[ -f "$dmg_path" && ! -f "$history_dir/$versioned_name-macOS-universal.dmg" ]]; then
    ditto "$dmg_path" "$history_dir/$versioned_name-macOS-universal.dmg"
  fi

  echo "已保留历史版本：$history_dir"
}

python3 -m unittest discover -s tests -v
archive_previous_release
python3 -m PyInstaller --clean --noconfirm photo_assistant.spec

if [[ "$sign_identity" == "-" ]]; then
  codesign --force --deep --sign - "$app_path"
else
  codesign \
    --force \
    --deep \
    --options runtime \
    --timestamp \
    --sign "$sign_identity" \
    "$app_path"
fi

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
