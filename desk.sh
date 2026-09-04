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
#   DESK_URL    (default http://127.0.0.1:8080)
#   DESK_TOKEN  (required for write ops — set in your shell profile)

set -euo pipefail

URL="${DESK_URL:-http://127.0.0.1:8080}"
TOKEN="${DESK_TOKEN:-}"

cmd="${1:-help}"

case "$cmd" in
  status)
    curl -s "$URL/api/state" | python3 -m json.tool
    ;;
  history)
    curl -s "$URL/api/history?limit=20" | python3 -m json.tool
    ;;
  help|--help|-h|"")
    cat <<EOF
Saga X Agent Desk CLI
  ./desk.sh status
  ./desk.sh history
  ./desk.sh <agent> <state> [task] [tool]

Agents:  putri, alisya, julia, farah, delisha
States:  idle, thinking, working, done, error, offline

Env:
  DESK_URL    Base URL (default http://127.0.0.1:8080)
  DESK_TOKEN  Auth token (required for status/history also work without)

To set token persistently:
  echo 'export DESK_TOKEN="your-token"' >> ~/.bashrc
  source ~/.bashrc
EOF
    ;;
  *)
    agent="$1"
    state="$2"
    task="${3-}"
    tool="${4-}"
    if [ -z "$TOKEN" ]; then
      echo "ERROR: DESK_TOKEN not set. Get token from your secrets manager." >&2
      echo "  export DESK_TOKEN=\"...\"" >&2
      exit 1
    fi
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
      -H "X-Saga-Token: $TOKEN" \
      -d "$payload" | python3 -m json.tool
    ;;
esac
