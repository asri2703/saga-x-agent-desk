# Saga X Agent Desk

Live dashboard for **Saga X Ventures Marketing Agency** — visualize Putri (CEO), Alisya (CTO), Julia (CFO), Farah (CMO), Delisha (COO) as animated anime avatars.

**Stack:** Pure stdlib Python 3 HTTP server + static HTML/CSS/SVG/JS. No npm, no pip install, no database.

## Quick start

```bash
python3 server.py
# Open http://localhost:8080
```

## Update agent state

```bash
curl -X POST http://localhost:8080/api/state \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"farah","state":"working","task":"Drafting caption"}'
```

Valid `agent_id`: `putri`, `alisya`, `julia`, `farah`, `delisha`
Valid `state`: `idle`, `thinking`, `working`, `done`, `error`, `offline`

## Deploy to production

See [DEPLOY.md](DEPLOY.md) — covers DNS, nginx, TLS, systemd, hardening.

## Project layout

```
server.py              ← HTTP server (stdlib only)
saga-x-desk.service    ← systemd unit
templates/index.html   ← dashboard shell
static/css/styles.css  ← theme + animations
static/js/avatars.js   ← 5 inline SVG anime characters
static/js/app.js       ← state polling + DOM updates
api/state.json         ← persistent state
logs/server.log        ← append-only log
DEPLOY.md              ← production deployment guide
```

## State semantics

| State | Animation | Color | Meaning |
|---|---|---|---|
| `idle` | breathing | grey | waiting for input |
| `thinking` | tilt + thought bubble | purple | planning / drafting |
| `working` | bouncing + typing dots | yellow | actively running |
| `done` | once-only bounce | green | task complete |
| `error` | shake | red | task failed |
| `offline` | dimmed | dark grey | disabled |
