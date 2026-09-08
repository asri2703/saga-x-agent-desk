# Saga X Agent Desk — VSCode Setup Guide

## Quick Start

1. **Download `saga-x-desk-source.tar.gz`** (29KB)
2. Extract to your local folder (e.g., `~/code/saga-x-desk/`)
3. Open folder in VSCode

## Recommended VSCode Extensions

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.debugpy",
    "NathanSilvestri.pretty-formatter",
    "esbenp.prettier-vscode",
    "ritwickdey.liveserver",
    "redhat.vscode-yaml"
  ]
}
```

## Project Structure

```
saga-x-desk/
├── server.py                 ← Python stdlib HTTP server (main entry)
├── scripts/
│   ├── domain_watch.py      ← Cron monitor (every 6h)
│   └── telegram_bridge.py   ← Telegram polling (disabled, kept for ref)
├── static/
│   ├── css/styles.css       ← All styling + animations
│   └── js/
│       ├── app.js           ← State polling + DOM update
│       └── avatars.js       ← 5 inline SVG avatars (3D-style anime)
├── templates/
│   └── index.html           ← Dashboard HTML
├── api/
│   └── state.json           ← Live state (created at runtime)
├── saga-x-desk.service      ← systemd unit
├── desk.sh                  ← CLI helper (update agent state)
├── DEPLOY.md                ← Production deployment guide
└── README.md
```

## Running Locally

```bash
# Install Python 3.10+ if needed
python3 --version

# Start server (port 8080)
python3 server.py

# Open in browser
# http://localhost:8080
```

## Development workflow

| Task | Command |
|---|---|
| Run server | `python3 server.py` |
| Test endpoint | `curl http://localhost:8080/api/state` |
| Update agent | `curl -X POST http://localhost:8080/api/state -H "Content-Type: application/json" -d '{"agent_id":"putri","state":"working","task":"testing"}'` |
| View logs | `tail -f logs/server.log` |

## VSCode Launch Config (`.vscode/launch.json`)

Create this for debugging:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run Desk Server",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/server.py",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}"
    }
  ]
}
```

## Production vs Development

**Dev (local):**
- POST `/api/state` no auth required (AUTH_REQUIRED=0)
- Logs to stdout
- State persists to local `api/state.json`

**Prod (deployed):**
- POST `/api/state` requires `X-Saga-Token` header (AUTH_REQUIRED=1)
- Logs to `logs/server.log` via systemd
- State persists to `/opt/saga-x-desk/api/state.json`
- Behind nginx + Cloudflare reverse proxy

## Key Files Explained

### `server.py` (main entry, ~330 lines)
- `BaseHTTPRequestHandler` subclass
- Routes: GET `/`, `/api/state`, `/api/history`, `/api/health`; POST `/api/state`, `/api/auth/test`, `/telegram/webhook/{secret}`
- Atomic state.json writes
- Env vars: `PORT`, `HOST`, `POST_TOKEN`, `AUTH_REQUIRED`, `TG_BOT_TOKEN`, `TG_WEBHOOK_SECRET`

### `static/js/avatars.js` (33KB)
- 5 avatar definitions as template literals
- Each returns inline SVG string
- State classes via CSS (idle/thinking/working/done/error/offline)

### `static/css/styles.css` (12KB)
- Ghibli-inspired dark theme
- 8 keyframe animations
- Responsive (mobile, iPad, desktop)

### `scripts/domain_watch.py`
- Cron job: every 6h check domains
- Updates Alisya state based on health
- SSL cert expiry warning

## Next Steps After Transfer

1. Test locally: `python3 server.py` → http://localhost:8080
2. Make changes (avatar style, add features)
3. Test on local iPad Safari (same WiFi, get IP: `ifconfig` on Linux/Mac)
4. When ready: commit + push to GitHub, deploy via `DEPLOY.md`

## Git Workflow

The `.git/` folder is excluded from the archive. To reconnect:

```bash
cd saga-x-desk
git init
git remote add origin https://github.com/asri2703/saga-x-agent-desk.git
git fetch origin
git checkout -b main origin/main
git branch --set-upstream-to=origin/main main
```

After that, normal git workflow.

## Need Help?

Just ask Putri (me!). I have full context of this project.
