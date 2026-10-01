#!/bin/zsh
# Requires a freshly approved VM run and a private connection file prepared by the developer.
set -euo pipefail
project_root="${0:A:h:h:h}"
app_path='/Applications/DeepSeek Harness.app'
run_id="${1:-}"
if (( $# != 1 )) || [[ ! "$run_id" =~ '^[A-Za-z0-9_-]{1,80}$' ]]; then
  print -u2 'usage: start-c0-desktop.sh <matching-guest-run-id>'
  exit 2
fi
if /usr/bin/pgrep -f '^/Applications/DeepSeek Harness.app/Contents/MacOS/DeepSeek Harness' >/dev/null; then
  print -u2 'Quit the existing Harness normally before switching its environment.'
  exit 2
fi
app_version=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$app_path/Contents/Info.plist")
[[ "$app_version" == '0.2.0-rc.2' ]] || exit 2
run_dir="$project_root/.runtime/runs/$run_id"
[[ -f "$run_dir/c0-connection.json" ]] || { print -u2 'Private matching VM connection is missing'; exit 2; }
exec /usr/bin/open --env "DSH_HOME=$project_root/.runtime/desktop-home" \
  --env "CUAGENT_C0_CONNECTION=$run_dir/c0-connection.json" \
  --env "CUAGENT_C0_AUDIT_PATH=$run_dir/request-audit.jsonl" -a "$app_path"
