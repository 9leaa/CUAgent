#!/bin/zsh
# Launch the official app with a persistent A0 run ledger and project plugins.
set -euo pipefail
project_root="${0:A:h:h:h}"
app_path='/Applications/DeepSeek Harness.app'
if [[ ! -d "$app_path" ]]; then
  print -u2 'Install the official DeepSeek Harness macOS app first.'
  exit 2
fi
desktop_home="$project_root/.runtime/desktop-home"
run_id="${1:-desktop_a0_$(date +%Y%m%d_%H%M%S)}"
if (( $# > 1 )) || [[ ! "$run_id" =~ '^[A-Za-z0-9_-]{1,80}$' ]]; then
  print -u2 'usage: start-desktop.sh [run-id]'
  exit 2
fi
app_version=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$app_path/Contents/Info.plist")
if [[ "$app_version" != '0.2.0-rc.2' ]]; then
  print -u2 "Desktop version $app_version needs adapter compatibility verification before launch."
  exit 2
fi
if /usr/bin/pgrep -f '^/Applications/DeepSeek Harness.app/Contents/MacOS/DeepSeek Harness' >/dev/null; then
  print -u2 'Quit DeepSeek Harness before launching a project run; open cannot replace a running process environment.'
  exit 2
fi
run_dir="$project_root/.runtime/runs/$run_id"
if [[ ! -f "$desktop_home/profiles/desktop/cuagent-plugins/build.json" ]]; then
  print -u2 'Build and configure the desktop adapters first; see agent/harness/README.md.'
  exit 2
fi
mkdir -p "$run_dir/workspace"
mkdir -p "$desktop_home"
chmod 700 "$desktop_home"
exec /usr/bin/open --env "DSH_HOME=$desktop_home" \
  --env "CUAGENT_A0_RUN_ID=$run_id" \
  --env "CUAGENT_A0_AUDIT_PATH=$run_dir/audit.jsonl" \
  --env "CUAGENT_A0_WORKSPACE_ROOT=$run_dir/workspace" -a "$app_path"
