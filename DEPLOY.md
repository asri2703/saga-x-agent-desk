# Saga X Agent Desk — Deploy Guide

Live dashboard for **Saga X Ventures Marketing Agency** — visualize Putri (CEO), Alisya (CTO), Julia (CFO), Farah (CMO), Delisha (COO) as animated anime avatars on `desk.sagaxventures.com`.

## What this is

- **Pure stdlib Python 3** HTTP server — no pip install, no npm build
- **5 SVG anime avatars** with state-driven CSS animations
- **State stored in `api/state.json`** — survives restarts, atomic writes
- **Two-way communication**: any tool (Putri, cron, webhook) updates state via `POST /api/state` → browser polls every 3s → animations reflect

## Architecture

```
Putri / cron / Telegram bot / CI webhook
        ↓
   POST /api/state  →  api/state.json  (atomic write)
                              ↓
                       GET /api/state  (every 3s)
                              ↓
                       Browser DOM update
                              ↓
                       CSS animations trigger
                              ↓
                       desk.sagaxventures.com
```

No backend runtime dependencies, no database, no build step.

## File layout

```
/home/ubuntu/desk-dashboard/
├── server.py              ← HTTP server (stdlib only)
├── saga-x-desk.service    ← systemd unit
├── templates/
│   └── index.html         ← dashboard shell
├── static/
│   ├── css/styles.css     ← Ghibli-inspired theme + animations
│   └── js/
│       ├── avatars.js     ← 5 inline SVG anime characters
│       └── app.js         ← state polling + DOM updates
├── api/
│   └── state.json         ← persistent state (atomic writes)
└── logs/
    └── server.log         ← append-only log
```

## Local test (already running)

```bash
cd /home/ubuntu/desk-dashboard
python3 server.py
# Open http://localhost:8080 in browser
```

Test the API:

```bash
# Health
curl http://localhost:8080/api/health

# Read state
curl http://localhost:8080/api/state

# Update one agent
curl -X POST http://localhost:8080/api/state \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"farah","state":"working","task":"Drafting caption","current_tool":"xurl"}'

# Try invalid agent (should 400)
curl -X POST http://localhost:8080/api/state \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"robot","state":"working"}'
```

## Production deploy on Saga X server

### Step 1 — Copy project to server

```bash
rsync -avz --exclude='logs/' --exclude='api/state.json' \
  /home/ubuntu/desk-dashboard/ \
  sagax@<saga-x-server>:/opt/saga-x-desk/
```

### Step 2 — Install systemd unit

```bash
ssh sagax@<saga-x-server>
sudo cp /opt/saga-x-desk/saga-x-desk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now saga-x-desk
sudo systemctl status saga-x-desk    # should show "active (running)"
```

Verify local access:

```bash
curl http://127.0.0.1:8080/api/health
```

### Step 3 — nginx reverse proxy + TLS

On the Saga X server, add to `/etc/nginx/sites-available/desk.sagaxventures.com.conf`:

```nginx
server {
    listen 80;
    server_name desk.sagaxventures.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name desk.sagaxventures.com;

    ssl_certificate     /etc/letsencrypt/live/desk.sagaxventures.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/desk.sagaxventures.com/privkey.pem;

    # Allow up to 60s for state polling
    proxy_read_timeout 60s;

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        # SSE/streaming friendly headers
        proxy_buffering    off;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/desk.sagaxventures.com.conf \
           /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 4 — TLS cert (Let's Encrypt)

```bash
sudo certbot --nginx -d desk.sagaxventures.com
# Auto-renews via certbot timer
```

### Step 5 — DNS

In **Cloudflare** dashboard for `sagaxventures.com`:

- Type: `A` (or `CNAME` if Saga X is behind another host)
- Name: `desk`
- Target: `<Saga X server public IP>`
- Proxy: **DNS only** (grey cloud) initially — can flip to orange once TLS works
- TTL: Auto

Verify:

```bash
dig desk.sagaxventures.com
curl -I https://desk.sagaxventures.com
```

## API reference

### `GET /api/state`

Returns current state of all 5 agents.

```json
{
  "putri": {
    "name": "Putri",
    "role": "CEO",
    "state": "thinking",
    "task": "Planning Q4 launch",
    "current_tool": "plan",
    "updated_at": 1788523119
  },
  "alisya": {...},
  "julia": {...},
  "farah": {...},
  "delisha": {...}
}
```

### `GET /api/health`

Returns `{ "ok": true, "uptime_s": <int> }`.

### `POST /api/state`

Update one agent. Body:

```json
{
  "agent_id": "putri|alisya|julia|farah|delisha",
  "state": "idle|thinking|working|done|error|offline",
  "task": "Free-text description (max 200 chars)",
  "current_tool": "Optional tool name shown as · tool"
}
```

Returns the updated agent record. Errors: `400` on invalid agent/state, `404` on bad path.

## State semantics

| State | Animation | Color | Use for |
|---|---|---|---|
| `idle` | gentle breathing | grey | waiting for input |
| `thinking` | head tilt + thought bubble + typing dots | purple | planning / drafting |
| `working` | bouncing + typing dots | yellow | actively running a tool |
| `done` | once-only bounce | green | task complete |
| `error` | shake | red | task failed, needs attention |
| `offline` | dimmed / grayscale | dark grey | agent disabled / session ended |

## Integration patterns

### Putri → state (manual)

From any agent process, after spawning a task:

```bash
curl -X POST http://127.0.0.1:8080/api/state \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"farah","state":"working","task":"Drafting TikTok caption"}'
```

When done:

```bash
curl -X POST http://127.0.0.1:8080/api/state \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"farah","state":"done","task":"Caption drafted, awaiting approval"}'
```

### Cron job updates

Add a cron entry that pings state on a schedule — e.g. weekly invoice generator:

```bash
0 9 * * MON curl -s -X POST http://127.0.0.1:8080/api/state \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"julia","state":"working","task":"Generating Monday invoice batch","current_tool":"xlsx"}'
```

### Telegram webhook (future)

A simple HTTP listener can translate Telegram bot events into state updates:

```python
# pseudocode — runs as a sibling service
@app.post("/telegram-webhook")
async def handle(update):
    if "draft" in update.message.text:
        agent = "farah"
        state = "working"
    desk.post_state(agent, state, update.message.text)
```

## Troubleshooting

**Dashboard shows "connecting…" forever**

- Check server: `systemctl status saga-x-desk`
- Check port: `ss -tlnp | grep 8080`
- Check nginx: `sudo nginx -t && sudo systemctl status nginx`
- Check DNS: `dig desk.sagaxventures.com`

**State updates don't reflect**

- Check `api/state.json` was written: `cat /home/ubuntu/desk-dashboard/api/state.json`
- Check server log: `tail /home/ubuntu/desk-dashboard/logs/server.log`
- Check browser console for fetch errors
- Hard refresh (Ctrl+Shift+R) — `state.json` may be cached

**Avatars look broken / no animation**

- Open browser DevTools → Console
- Verify `/static/js/avatars.js` and `/static/js/app.js` load (200)
- Verify `/static/css/styles.css` loads (200)

## Hardening checklist

- [ ] Service runs as non-root (`User=ubuntu` in unit file — already done)
- [ ] State file permissions: `chmod 600 /home/ubuntu/desk-dashboard/api/state.json`
- [ ] Reverse proxy via nginx (never expose 8080 directly)
- [ ] TLS via Let's Encrypt (`certbot`)
- [ ] Cloudflare proxy on (orange cloud) for DDoS protection
- [ ] Fail2ban for nginx-auth (optional, dashboard is read-only so low priority)

## Phase 2 (later)

- [ ] Auth: simple shared-secret header for `POST /api/state`
- [ ] Token/cost tracking per agent (parse from session DB)
- [ ] Activity heatmap (last 30 days)
- [ ] Slack/Telegram integration for state changes
- [ ] Mobile-app-style install (PWA manifest)
