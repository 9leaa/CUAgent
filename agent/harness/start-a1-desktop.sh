#!/bin/zsh
# Dedicated A1 launch. Task config is pre-approved by the developer, never the model.
set -euo pipefail
project_root="${0:A:h:h:h}"
app_path='/Applications/DeepSeek Harness.app'
if (( $# != 1 )) || [[ "$1" != /* ]] || [[ ! -f "$1" ]]; then
  print -u2 'usage: /bin/zsh start-a1-desktop.sh /absolute/private/tasks.json'
  exit 2
fi
if /usr/bin/pgrep -f '^/Applications/DeepSeek Harness.app/Contents/MacOS/DeepSeek Harness' >/dev/null; then
  print -u2 'Quit the App normally after confirming all turns are terminal; no live environment switch.'
  exit 2
fi
app_version=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$app_path/Contents/Info.plist")
if [[ "$app_version" != '0.2.0-rc.2' ]]; then
  print -u2 'A1 requires a separately reviewed Desktop version.'
  exit 2
fi
node "$project_root/agent/harness/validate-a1-launch.mjs" "$1"
desktop_home="$project_root/.runtime/desktop-home"
exec /usr/bin/open --env "DSH_HOME=$desktop_home" \
  --env "CUAGENT_A1_TASKS_PATH=$1" -a "$app_path"
