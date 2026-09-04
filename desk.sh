#!/usr/bin/env bash
# Saga X Desk — convenience CLI
# Update agent state from terminal without remembering curl flags.
#
# Usage:
#   ./desk.sh farah working "Drafting TikTok caption" xurl
#   ./desk.sh alisya idle
#   ./desk.sh julia done "Invoice batch ready"
#   ./desk.sh status            # show current state
#
# Env:
#   DESK_URL (default http://127.0.0.1:8080)

set -euo pipefail

URL="${DESK_URL:-http://127.0.0.1:8080}"

cmd="${1:-help}"

case "$cmd" in
  status)
    curl -s "$URL/api/state" | python3 -m json.tool
    ;;
  help|--help|-h|"")
    cat <<EOF
Saga X Agent Desk CLI
  ./desk.sh status
  ./desk.sh <agent> <state> [task] [tool]

Agents:  putri, alisya, julia, farah, delisha
States:  idle, thinking, working, done, error, offline

Env:
  DESK_URL  Base URL (default http://127.0.0.1:8080)
EOF
    ;;
  *)
    agent="$1"
    state="$2"
    task="${3-}"
    tool="${4-}"
    payload=$(python3 -c "
import json, sys
print(json.dumps({
    'agent_id': sys.argv[1],
    'state': sys.argv[2],
    'task': sys.argv[3],
    'current_tool': sys.argv[4] or None,
}))
" "$agent" "$state" "$task" "$tool")
    curl -s -X POST "$URL/api/state" \
      -H "Content-Type: application/json" \
      -d "$payload" | python3 -m json.tool
    ;;
esac
