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

python3 -m unittest discover -s tests -v
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
