#!/usr/bin/env bash
# ============================================================
# Saga X Agent Desk — deploy to the VPS
# ============================================================
#   ./deploy.sh --dry-run     show what would happen, touch nothing
#   ./deploy.sh               deploy
#   ./deploy.sh --no-restart  copy and install, leave the service alone
#
# Reads .env for the connection details. Secrets travel over SSH and
# land in /etc/saga-x-desk/env owned by root, mode 600 — never inside
# the app directory, which is world-readable and gets rsynced over.
#
# Safe to re-run. Everything here is idempotent.
# ============================================================

set -euo pipefail

DRY_RUN=0
RESTART=1
for arg in "$@"; do
  case "$arg" in
    --dry-run)    DRY_RUN=1 ;;
    --no-restart) RESTART=0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

cd "$(dirname "$0")"

[ -f .env ] || { echo "ERROR: .env not found" >&2; exit 1; }

# Read .env without exporting it into this shell wholesale — we only
# want the deployment variables here, not the API keys.
get_env() {
  sed -n "s/^$1=//p" .env | head -1 | sed 's/[[:space:]]*#.*$//' | tr -d '\r'
}

VPS_HOST="$(get_env VPS_HOST)"
VPS_SSH_USER="$(get_env VPS_SSH_USER)"
VPS_SSH_KEY_PATH="$(get_env VPS_SSH_KEY_PATH)"
VPS_APP_DIR="$(get_env VPS_APP_DIR)"
VPS_APP_DIR="${VPS_APP_DIR:-/opt/saga-x-desk}"

missing=""
for v in VPS_HOST VPS_SSH_USER VPS_SSH_KEY_PATH; do
  [ -n "${!v}" ] || missing="$missing $v"
done
if [ -n "$missing" ]; then
  echo "ERROR: not set in .env:$missing" >&2
  echo "See VPS_SETUP.md." >&2
  exit 1
fi

# Windows paths land here as C:/Users/...; ssh wants /c/Users/...
case "$VPS_SSH_KEY_PATH" in
  [A-Za-z]:/*) VPS_SSH_KEY_PATH="/$(echo "${VPS_SSH_KEY_PATH:0:1}" | tr 'A-Z' 'a-z')${VPS_SSH_KEY_PATH:2}" ;;
esac

[ -f "$VPS_SSH_KEY_PATH" ] || {
  echo "ERROR: no key file at $VPS_SSH_KEY_PATH" >&2; exit 1; }

SSH="ssh -i $VPS_SSH_KEY_PATH -o StrictHostKeyChecking=accept-new $VPS_SSH_USER@$VPS_HOST"
TARGET="$VPS_SSH_USER@$VPS_HOST"

say()  { printf '\n\033[1m== %s\033[0m\n' "$1"; }
run()  { if [ "$DRY_RUN" = 1 ]; then echo "  would: $*"; else eval "$@"; fi; }

echo "host    : $TARGET"
echo "app dir : $VPS_APP_DIR"
echo "key     : $VPS_SSH_KEY_PATH"
[ "$DRY_RUN" = 1 ] && echo "MODE    : dry run, nothing will change"

# ── 1. Local checks before touching anything remote ─────────
say "1. Local preflight"
if [ "$DRY_RUN" = 0 ]; then
  python -m agents.preflight >/dev/null 2>&1 || {
    echo "  local preflight failed — fix that before deploying" >&2
    python -m agents.preflight 2>&1 | tail -20
    exit 1; }
  echo "  ok"
else
  echo "  would run: python -m agents.preflight"
fi

# ── 2. Reachability ─────────────────────────────────────────
say "2. SSH"
if [ "$DRY_RUN" = 0 ]; then
  $SSH "echo '  connected as' \$(whoami) 'on' \$(hostname)"
else
  echo "  would: $SSH"
fi

# ── 3. Copy the app ─────────────────────────────────────────
# .env is excluded on purpose. Production reads its configuration from
# the systemd env file, so a stale local .env can never override it.
say "3. Copy application"
RSYNC_EXCLUDES=(
  --exclude '.git' --exclude '.env' --exclude '.env.*'
  --exclude '__pycache__' --exclude '*.pyc'
  --exclude '_archive' --exclude '.venv' --exclude 'logs/*'
  --exclude 'api/state.json' --exclude 'api/history.jsonl'
  --exclude '.vscode' --exclude 'dot-env-*'
)
run "$SSH \"mkdir -p $VPS_APP_DIR/logs $VPS_APP_DIR/api\""
# Not through run()/eval: eval would glob-expand patterns like `logs/*`
# against the local directory, turning an exclude rule into a list of
# real filenames and silently shipping the files it was meant to skip.
EXCLUDE_NAMES=(
  '.git' '.env' '__pycache__' '_archive' '.venv' '.vscode'
  'api/state.json' 'api/history.jsonl'
)
if [ "$DRY_RUN" = 1 ]; then
  echo "  would copy the app, excluding ${#EXCLUDE_NAMES[@]} paths"
elif command -v rsync >/dev/null 2>&1; then
  rsync -az --delete "${RSYNC_EXCLUDES[@]}" \
    -e "ssh -i $VPS_SSH_KEY_PATH -o StrictHostKeyChecking=accept-new" \
    ./ "$TARGET:$VPS_APP_DIR/"
  echo "  copied (rsync)"
else
  # Git Bash on Windows ships no rsync. tar over ssh is portable and
  # needs nothing installed. It cannot delete files removed locally, so
  # a file dropped from the repo lingers on the VM until cleaned by hand.
  echo "  rsync not found locally — using tar over ssh"
  TAR_EXCLUDES=()
  for e in "${EXCLUDE_NAMES[@]}"; do TAR_EXCLUDES+=(--exclude="$e"); done
  TAR_EXCLUDES+=(--exclude='*.pyc' --exclude='.env.*' --exclude='dot-env-*'
                 --exclude='logs/*.log')
  tar czf - "${TAR_EXCLUDES[@]}" . \
    | $SSH "tar xzf - -C $VPS_APP_DIR && echo '  copied (tar)'"
fi

# ── 4. Dependencies ─────────────────────────────────────────
say "4. Python environment"
run "$SSH \"cd $VPS_APP_DIR && python3 -m venv .venv 2>/dev/null; \
  .venv/bin/pip install --quiet --upgrade pip && \
  .venv/bin/pip install --quiet -r requirements.txt && \
  echo '  deps installed'\""

# ── 5. Secrets ──────────────────────────────────────────────
# Only the runtime keys. HOST is forced to 0.0.0.0 because nginx
# proxies to it; AUTH_REQUIRED is forced on because this is a public URL.
say "5. Environment file (root-owned, 0600)"
if [ "$DRY_RUN" = 1 ]; then
  echo "  would write /etc/saga-x-desk/env with the runtime keys"
else
  # Ship everything except what the VM must not or need not have.
  # An allowlist was the original approach and it silently dropped every
  # variable added afterwards — VAPID keys and CTO_API_KEY both reached
  # production empty, and the only symptom was a feature quietly not
  # working. Excluding is the safer default: a new var ships by itself.
  # Excluded: deploy-only tooling (GCP/VPS), values the unit forces
  # (HOST/PORT/AUTH), and credentials the running app never calls —
  # CLOUDFLARE_API_TOKEN can rewrite DNS for the whole domain and
  # SUPABASE_DB_PASSWORD is superseded by DATABASE_URL. A key with no
  # use on the box is pure risk if the box is ever compromised.
  SKIP='^(GCP_|VPS_|GITHUB_|CLOUDFLARE_|SUPABASE_DB_PASSWORD=|HOST=|PORT=|AUTH_REQUIRED=|CORS_ALLOWED_ORIGINS=)'
  {
    echo "# Generated by deploy.sh — do not edit by hand"
    grep -vE '^\s*(#|$)' .env \
      | grep -vE "$SKIP" \
      | sed 's/[[:space:]]*#.*$//' \
      | sed 's/[[:space:]]*$//' \
      | grep -E '^[A-Z_][A-Z0-9_]*=.+'
    echo "HOST=0.0.0.0"
    echo "PORT=8080"
    echo "AUTH_REQUIRED=1"
  # Owned by the app user, not root: systemd reads it as root either way,
  # but the cron jobs run as this user and must be able to source it.
  # Mode 600 still means nobody else on the box can read the keys.
  } | $SSH "sudo mkdir -p /etc/saga-x-desk && sudo tee /etc/saga-x-desk/env >/dev/null \
      && sudo chown $VPS_SSH_USER:$VPS_SSH_USER /etc/saga-x-desk/env \
      && sudo chmod 600 /etc/saga-x-desk/env \
      && ls -l /etc/saga-x-desk/env"
fi

# ── 6. Import the state this replaces ───────────────────────
say "6. Import legacy state"
if [ "$DRY_RUN" = 1 ]; then
  echo "  would run import_legacy() on the VM (dry run first, then real)"
else
  $SSH "cd $VPS_APP_DIR && set -a && . /etc/saga-x-desk/env && set +a && \
    .venv/bin/python -c \"
from agents import state
print('  dry run:', state.import_legacy(dry_run=True))
print('  applied:', state.import_legacy(dry_run=False))\""
fi

# ── 7. systemd ──────────────────────────────────────────────
say "7. Service"
if [ "$DRY_RUN" = 1 ]; then
  echo "  would install saga-x-desk.service and reload systemd"
else
  $SSH "sudo tee /etc/systemd/system/saga-x-desk.service >/dev/null <<UNIT
[Unit]
Description=Saga X Agent Desk
After=network-online.target

[Service]
Type=simple
User=$VPS_SSH_USER
WorkingDirectory=$VPS_APP_DIR
EnvironmentFile=/etc/saga-x-desk/env
ExecStart=$VPS_APP_DIR/.venv/bin/python $VPS_APP_DIR/server.py
Restart=always
RestartSec=5
StandardOutput=append:$VPS_APP_DIR/logs/server.log
StandardError=append:$VPS_APP_DIR/logs/server.log

[Install]
WantedBy=multi-user.target
UNIT
  sudo systemctl daemon-reload && sudo systemctl enable saga-x-desk >/dev/null && echo '  unit installed'"
fi

# ── 8. Cron ─────────────────────────────────────────────────
# Written as one managed block so re-running replaces rather than
# duplicates. Duplicated cron entries double the API spend silently.
say "8. Cron"
if [ "$DRY_RUN" = 1 ]; then
  echo "  would install: scheduler /15min, monitors /6h, notify /5min"
else
  $SSH "( crontab -l 2>/dev/null | grep -v '# saga-x-desk' ; cat <<CRON
*/15 * * * * cd $VPS_APP_DIR && set -a && . /etc/saga-x-desk/env && set +a && .venv/bin/python -m agents.scheduler >> logs/scheduler.log 2>&1 # saga-x-desk
0 */6 * * * cd $VPS_APP_DIR && set -a && . /etc/saga-x-desk/env && set +a && .venv/bin/python -m agents.monitors >> logs/monitors.log 2>&1 # saga-x-desk
*/5 * * * * cd $VPS_APP_DIR && set -a && . /etc/saga-x-desk/env && set +a && .venv/bin/python -m agents.notify >> logs/notify.log 2>&1 # saga-x-desk
CRON
  ) | crontab - && echo '  3 entries installed'"
fi

# ── 9. Restart and verify ───────────────────────────────────
if [ "$RESTART" = 1 ]; then
  say "9. Restart"
  run "$SSH \"sudo systemctl restart saga-x-desk && sleep 3 && \
    systemctl is-active saga-x-desk\""

  say "10. Verify on the VM"
  if [ "$DRY_RUN" = 0 ]; then
    $SSH "cd $VPS_APP_DIR && set -a && . /etc/saga-x-desk/env && set +a && \
      .venv/bin/python -m agents.preflight" || {
        echo "  preflight FAILED on the VM — check the output above" >&2; exit 1; }
    $SSH "curl -s -o /dev/null -w '  local health: %{http_code}\n' http://127.0.0.1:8080/api/health"
  fi
else
  say "9. Restart skipped (--no-restart)"
fi

say "Done"
echo "Next, once nginx and certbot are configured per DEPLOY.md:"
echo "  curl -I https://desk.sagaxventures.com"
