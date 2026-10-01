#!/bin/zsh
set -euo pipefail
project_root="${0:A:h:h:h}"
app_dir="$project_root/.runtime/CUAgentFixtures.app"
mkdir -p "$app_dir/Contents/MacOS"
/usr/bin/xcrun clang -arch arm64 -mmacosx-version-min=15.0 -fobjc-arc -framework Cocoa \
  "$project_root/tools/mac_vm/fixtures/CUAgentFixtures.m" -o "$app_dir/Contents/MacOS/CUAgentFixtures"
/bin/cp "$project_root/tools/mac_vm/fixtures/Info.plist" "$app_dir/Contents/Info.plist"
/usr/bin/codesign --force --sign - "$app_dir"
/usr/bin/codesign --verify --strict "$app_dir"
print 'Built signed arm64 GUI fixture. VM guard prevents host execution.'
