#!/bin/zsh
# Start the dedicated A0 Web profile. Reuse the same run id after a restart so
# its append-only audit ledger (and 30-call budget) cannot reset accidentally.
set -euo pipefail
if (( $# < 1 || $# > 2 )); then
  print -u2 'usage: start-a0-web.sh <run-id> [port]'
  exit 2
fi
run_id="$1"
port="${2:-3099}"
if [[ ! "$run_id" =~ '^[A-Za-z0-9_-]{1,80}$' || ! "$port" =~ '^[0-9]{1,5}$' ]]; then
  print -u2 'invalid A0 run id or port'
  exit 2
fi
if (( port < 1 || port > 65535 )); then
  print -u2 'A0 port must be between 1 and 65535'
  exit 2
fi
if [[ -e /Users/zhangchengjie/CUAgent/.runtime/harness-home/cordis.patch.yml ]]; then
  print -u2 'global DSH_HOME patch would make the A0 profile ambiguous'
  exit 2
fi
profile_patch=/Users/zhangchengjie/CUAgent/.runtime/harness-home/profiles/cuagent-a0/cordis.patch.yml
expected_patch=/Users/zhangchengjie/CUAgent/agent/harness/cordis.a0.profile.patch.yml
if [[ ! -L "$profile_patch" || "$(readlink "$profile_patch")" != "$expected_patch" ]]; then
  print -u2 'A0 profile patch is missing or differs from the reviewed source'
  exit 2
fi
run_dir="/Users/zhangchengjie/CUAgent/.runtime/runs/$run_id"
mkdir -p "$run_dir/workspace"
export CUAGENT_A0_RUN_ID="$run_id"
export CUAGENT_A0_AUDIT_PATH="$run_dir/audit.jsonl"
export CUAGENT_A0_WORKSPACE_ROOT="$run_dir/workspace"
cd /Users/zhangchengjie/CUAgent/.runtime/harness || exit 1
export DSH_HOME=/Users/zhangchengjie/CUAgent/.runtime/harness-home
exec node --import tsx/esm apps/cli/src/bin.ts \
  --profile cuagent-a0 \
  --port "$port" --no-open
