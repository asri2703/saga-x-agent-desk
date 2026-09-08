#!/usr/bin/env python3
"""
Saga X Marketing Agency — Agent Desk Dashboard Server
=====================================================
Standalone HTTP server (stdlib only — no pip dependencies).

Serves:
  GET  /              → dashboard HTML (animated avatars)
  GET  /api/state     → JSON state of all agents
  POST /api/state     → update one agent's state (Putri or any updater)
  GET  /static/*      → CSS/JS/SVG assets

State is persisted to api/state.json so dashboard survives restarts.
Designed to be trivial to deploy:
  - No build step
  - No pip install
  - No database
  - Plain Python 3.x stdlib

Env vars:
  PORT  (default 8080)
  HOST  (default 0.0.0.0)
"""

import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).parent
STATE_FILE = ROOT / "api" / "state.json"
LOG_FILE = ROOT / "logs" / "server.log"
HISTORY_FILE = ROOT / "api" / "history.jsonl"

# Auth: shared secret for state-changing endpoints.
# Set via env var POST_TOKEN; falls back to default for dev convenience.
POST_TOKEN = os.environ.get("POST_TOKEN", "saga-x-dev-token-change-me")
# What a person types on the dashboard. Kept separate from POST_TOKEN,
# which cron and curl send as X-Saga-Token: rotating the one you type
# should not stop the scheduler, and a machine token should not have to
# be typeable on a phone. Falls back to POST_TOKEN if unset.
DESK_PASSWORD = os.environ.get("DESK_PASSWORD", "") or POST_TOKEN
AUTH_REQUIRED = os.environ.get("AUTH_REQUIRED", "0") == "1"

# Telegram webhook secret — random token in URL path for auth
# Generate via: python3 -c "import secrets; print(secrets.token_urlsafe(24))"
TG_WEBHOOK_SECRET = os.environ.get("TG_WEBHOOK_SECRET", "saga-x-tg-dev-secret")

# Exact origins allowed to call the API cross-origin. Empty = same-origin
# only, which is the correct answer while one process serves both.
CORS_ALLOWED_ORIGINS = {
    o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
}

# Valid agent IDs (must match dashboard avatars)
VALID_AGENTS = {"putri", "alisya", "julia", "farah", "delisha"}

# Valid states
VALID_STATES = {"idle", "thinking", "working", "done", "error", "offline"}

# Telegram bot config
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_STATE_EMOJI = {
    "idle": "💤", "thinking": "💭", "working": "⚡",
    "done": "✅", "error": "❌", "offline": "⚫",
}
TG_HELP_TEXT = """🤖 *Saga X Agent Desk Bot*

Commands:
  /desk\\_status — show all 5 agents
  /desk\\_set <agent> <state> [task] — update agent
  /desk\\_history [N] — last N updates (default 5)
  /desk\\_help — this message

Agents: `putri alisya julia farah delisha`
States: `idle thinking working done error offline`

Example:
  `/desk_set farah working Drafting TikTok caption`
"""


def tg_send(chat_id: int, text: str) -> bool:
    """Send a message via Telegram Bot API. Returns True on success."""
    if not TG_BOT_TOKEN:
        log("TG_BOT_TOKEN not set, cannot send reply")
        return False
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "SagaXDesk/1.0",
            "Accept-Language": "en-US,en;q=0.9",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read())
            if not body.get("ok"):
                log(f"TG send fail: {body}")
            return body.get("ok", False)
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        log(f"TG send error: {e}")
        return False

# Default state — used on first run
DEFAULT_STATE = {
    "putri": {
        "name": "Putri",
        "role": "CEO",
        "state": "idle",
        "task": "Awaiting orders",
        "current_tool": None,
        "updated_at": None,
    },
    "alisya": {
        "name": "Alisya",
        "role": "CTO",
        "state": "idle",
        "task": "Idle",
        "current_tool": None,
        "updated_at": None,
    },
    "julia": {
        "name": "Julia",
        "role": "CFO",
        "state": "idle",
        "task": "Idle",
        "current_tool": None,
        "updated_at": None,
    },
    "farah": {
        "name": "Farah",
        "role": "CMO",
        "state": "idle",
        "task": "Idle",
        "current_tool": None,
        "updated_at": None,
    },
    "delisha": {
        "name": "Delisha",
        "role": "COO",
        "state": "idle",
        "task": "Idle",
        "current_tool": None,
        "updated_at": None,
    },
}


# ─── Storage backend ─────────────────────────────────────────────
# State lives in Postgres (desk.agent_state). The JSON file it used to
# live in is kept as a mirror so a database outage degrades to slightly
# stale rather than to a broken dashboard.
#
# If the agents package cannot be imported at all — psycopg missing on
# a half-finished deploy, say — we fall back to the original file-based
# behaviour rather than take the desk down. A live system should not
# die because a new dependency has not landed yet.
try:
    from agents import state as agent_state
    DB_BACKED = True
except Exception as _e:  # noqa: BLE001 — any import failure means fall back
    agent_state = None
    DB_BACKED = False
    _DB_IMPORT_ERROR = _e


def _load_state_file() -> dict:
    """The original file-based read. Fallback path only."""
    if not STATE_FILE.exists():
        _save_state_file(DEFAULT_STATE)
        return DEFAULT_STATE
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            state = json.load(f)
        for k, v in DEFAULT_STATE.items():
            state.setdefault(k, v)
        return state
    except (json.JSONDecodeError, OSError) as e:
        log(f"State corrupt, resetting: {e}")
        _save_state_file(DEFAULT_STATE)
        return DEFAULT_STATE


def _save_state_file(state: dict) -> None:
    """Atomic write — .tmp then rename, to avoid partial reads."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    tmp.replace(STATE_FILE)


def load_state() -> dict:
    """All agents, in the shape /api/state has always returned."""
    if DB_BACKED:
        try:
            return agent_state.load_state()
        except Exception as e:
            log(f"DB read failed, serving mirror: {e}")
    return _load_state_file()


def save_state(state: dict) -> None:
    """Kept for callers that still hand back a whole state dict."""
    if DB_BACKED:
        try:
            for agent_id, data in state.items():
                agent_state.set_state(
                    agent_id,
                    data.get("state", "idle"),
                    data.get("task", ""),
                    data.get("current_tool"),
                )
            return
        except Exception as e:
            log(f"DB write failed, writing mirror only: {e}")
    _save_state_file(state)


def set_agent(agent_id: str, new_state: str, task: str = "",
              tool: str | None = None) -> dict:
    """Update one agent and record the change. Single write path for
    both the HTTP endpoint and the Telegram command, so history can
    never be recorded by one and missed by the other."""
    if DB_BACKED:
        try:
            return agent_state.set_state(agent_id, new_state, task, tool)
        except Exception as e:
            log(f"DB write failed for {agent_id}, falling back to file: {e}")

    state = _load_state_file()
    state[agent_id]["state"] = new_state
    state[agent_id]["task"] = str(task)[:200]
    state[agent_id]["current_tool"] = tool
    state[agent_id]["updated_at"] = int(time.time())
    _save_state_file(state)
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": state[agent_id]["updated_at"], "agent": agent_id,
                "state": new_state, "task": state[agent_id]["task"],
                "tool": tool,
            }, ensure_ascii=False) + "\n")
    except OSError as e:
        log(f"history append failed: {e}")
    return state[agent_id]


def read_history(limit: int) -> dict:
    """Newest first, in the shape /api/history has always returned."""
    if DB_BACKED:
        try:
            return agent_state.history(limit)
        except Exception as e:
            log(f"DB history read failed, reading file: {e}")
    entries = []
    if HISTORY_FILE.exists():
        try:
            with HISTORY_FILE.open("r", encoding="utf-8") as f:
                for line in reversed(f.readlines()[-limit:]):
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            log(f"history read failed: {e}")
    return {"entries": entries, "count": len(entries)}


def log(msg: str) -> None:
    """Append-only log to logs/server.log + stdout."""
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass
    sys.stdout.write(line)
    sys.stdout.flush()


SESSION_DAYS = 30


def _make_session(days: int = SESSION_DAYS) -> str:
    """`expiry.signature`, signed with POST_TOKEN.

    Stateless on purpose — no session store to keep, and changing
    POST_TOKEN invalidates every outstanding session at once, which is
    the behaviour you want from a logout-everywhere switch.
    """
    expiry = str(int(time.time()) + days * 86400)
    sig = hmac.new(POST_TOKEN.encode(), expiry.encode(), hashlib.sha256).hexdigest()
    return f"{expiry}.{sig}"


def _valid_session(cookie: str) -> bool:
    if not cookie or "." not in cookie:
        return False
    expiry, _, sig = cookie.partition(".")
    expected = hmac.new(POST_TOKEN.encode(), expiry.encode(),
                        hashlib.sha256).hexdigest()
    # compare_digest, not ==, so a wrong signature cannot be found one
    # character at a time by timing the response.
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        return int(expiry) > time.time()
    except ValueError:
        return False


def _jsonable(value):
    """Postgres hands back datetime, Decimal and UUID objects; json.dumps
    will not serialise any of them."""
    from datetime import date, datetime as _dt
    from decimal import Decimal
    if isinstance(value, (_dt, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    return str(value)


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "SagaXDesk/1.0"

    def log_message(self, fmt: str, *args) -> None:
        """Route stdlib access logs through our logger."""
        log(f"{self.address_string()} {fmt % args}")

    # ─── GET handlers ────────────────────────────────────────────────

    def do_GET(self) -> None:
        self._handle_get(send_body=True)

    def do_HEAD(self) -> None:
        self._handle_get(send_body=False)

    def _handle_get(self, send_body: bool) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_file(ROOT / "templates" / "index.html", "text/html; charset=utf-8", send_body)
        elif path == "/api/state":
            self._json_response(200, load_state())
        elif path == "/api/health":
            self._json_response(200, {"ok": True, "uptime_s": int(time.time() - SERVER_START)})
        elif path == "/api/history":
            # Read recent history entries (newest first, capped)
            limit = 100
            try:
                if "limit" in parse_qs(parsed.query):
                    limit = min(int(parse_qs(parsed.query)["limit"][0]), 1000)
            except (ValueError, KeyError):
                pass
            self._json_response(200, read_history(limit))
        elif path.startswith("/api/chat/"):
            if not DB_BACKED:
                return self._json_response(503, {"error": "agent layer unavailable"})
            agent = path[len("/api/chat/"):].strip("/")
            try:
                from agents import chat
                self._json_response(200, {"agent": agent,
                                          "messages": chat.history(agent)})
            except ValueError as e:
                self._json_response(400, {"error": str(e)})
            except Exception as e:
                log(f"chat history failed: {e}")
                self._json_response(500, {"error": "chat unavailable"})
        elif path == "/sw.js":
            # Root scope on purpose: a service worker only controls the
            # path it is served from. At /static/js/sw.js it would
            # control /static/ and push would never reach the desk.
            self._serve_file(ROOT / "sw.js",
                             "application/javascript; charset=utf-8", send_body)
        elif path == "/manifest.json":
            self._serve_file(ROOT / "static" / "manifest.json",
                             "application/manifest+json; charset=utf-8", send_body)
        elif path == "/api/push/key":
            try:
                from agents import webpush
                self._json_response(200, {"public_key": webpush.public_key(),
                                          "configured": webpush.configured()})
            except Exception as e:
                self._json_response(500, {"error": str(e)[:150]})
        elif path == "/api/activity":
            if not DB_BACKED:
                return self._json_response(503, {"error": "agent layer unavailable"})
            days = 7
            try:
                q = parse_qs(parsed.query)
                if "days" in q:
                    days = int(q["days"][0])
            except (ValueError, KeyError):
                pass
            try:
                from agents import activity
                self._json_response(200, _jsonable(activity.summary(days)))
            except Exception as e:
                log(f"activity failed: {e}")
                self._json_response(500, {"error": str(e)[:200]})
        elif path == "/api/session":
            self._json_response(200, {
                "auth_required": AUTH_REQUIRED,
                "signed_in": self._authorised(),
            })
        elif path == "/api/approvals":
            if not DB_BACKED:
                return self._json_response(503, {"error": "agent layer unavailable"})
            try:
                from agents import approvals
                rows = approvals.pending()
                self._json_response(200, {"count": len(rows),
                                          "approvals": _jsonable(rows)})
            except Exception as e:
                log(f"approvals list failed: {e}")
                self._json_response(500, {"error": "approvals unavailable"})
        elif path.startswith("/static/"):
            self._serve_static(path, send_body)
        else:
            self._json_response(404, {"error": "not found", "path": path})

    # ─── POST handlers ───────────────────────────────────────────────

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/state":
            # Auth check (only when AUTH_REQUIRED=1)
            if AUTH_REQUIRED:
                provided = self.headers.get("X-Saga-Token", "")
                if provided != POST_TOKEN:
                    log(f"AUTH FAIL from {self.address_string()} (no/bad token)")
                    return self._json_response(401, {"error": "unauthorized"})

            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return self._json_response(400, {"error": "invalid JSON", "detail": str(e)})

            # Validate
            agent_id = payload.get("agent_id")
            if agent_id not in VALID_AGENTS:
                return self._json_response(
                    400,
                    {
                        "error": "unknown agent",
                        "agent_id": agent_id,
                        "valid": sorted(VALID_AGENTS),
                    },
                )
            new_state = payload.get("state")
            if new_state not in VALID_STATES:
                return self._json_response(
                    400,
                    {"error": "invalid state", "valid": sorted(VALID_STATES)},
                )

            # One write path — state and history move together.
            agent = set_agent(
                agent_id,
                new_state,
                str(payload.get("task", ""))[:200],
                payload.get("current_tool"),
            )

            log(f"STATE {agent_id} -> {new_state} task={agent['task']!r}")
            self._json_response(200, {"ok": True, "agent_id": agent_id, "state": agent})
        elif path.startswith("/api/chat/"):
            if not DB_BACKED:
                return self._json_response(503, {"error": "agent layer unavailable"})
            if not self._authorised():
                return self._json_response(401, {"error": "unauthorized"})
            rest = path[len("/api/chat/"):].strip("/")
            agent, _, action = rest.partition("/")
            body = self._read_json()
            if body is None:
                return self._json_response(400, {"error": "invalid JSON"})
            try:
                from agents import chat
                if action == "clear":
                    n = chat.clear(agent)
                    return self._json_response(200, {"ok": True, "deleted": n})
                # A model call takes seconds, not milliseconds. Threading
                # HTTPServer handles one per thread, so this blocks only
                # the caller.
                result = chat.send(agent, body.get("message", ""),
                                   effort=body.get("effort"))
                log(f"CHAT {agent} status={result.get('status')} "
                    f"cost=${result.get('cost_usd') or 0:.5f}")
                self._json_response(200, result)
            except ValueError as e:
                self._json_response(400, {"error": str(e)})
            except Exception as e:
                log(f"chat send failed: {e}")
                self._json_response(500, {"error": str(e)[:200]})
        elif path.startswith("/api/approvals/"):
            if not DB_BACKED:
                return self._json_response(503, {"error": "agent layer unavailable"})
            # Approving creates real invoices and moves real money figures.
            # Same gate as any other write.
            if not self._authorised():
                return self._json_response(401, {"error": "unauthorized"})
            rest = path[len("/api/approvals/"):].strip("/")
            approval_id, _, action = rest.partition("/")
            body = self._read_json() or {}
            try:
                from agents import approvals
                if action == "approve":
                    result = approvals.approve(approval_id, via="dashboard")
                elif action == "reject":
                    result = approvals.reject(approval_id, via="dashboard",
                                              reason=body.get("reason", ""))
                else:
                    return self._json_response(404, {"error": "unknown action"})
                log(f"APPROVAL {action} {approval_id}")
                self._json_response(200, _jsonable(result))
            except Exception as e:
                self._json_response(400, {"error": str(e)[:300]})
        elif path.startswith("/api/push/"):
            if not DB_BACKED:
                return self._json_response(503, {"error": "agent layer unavailable"})
            if not self._authorised():
                return self._json_response(401, {"error": "unauthorized"})
            action = path[len("/api/push/"):].strip("/")
            body = self._read_json() or {}
            try:
                from agents import webpush
                if action == "subscribe":
                    res = webpush.subscribe(
                        body.get("subscription") or {},
                        user_agent=self.headers.get("User-Agent", ""),
                        label=body.get("label", ""))
                elif action == "unsubscribe":
                    res = webpush.unsubscribe(body.get("endpoint", ""))
                elif action == "test":
                    res = webpush.send("Saga X Desk",
                                       "Notifikasi berfungsi.", url="/")
                else:
                    return self._json_response(404, {"error": "unknown action"})
                self._json_response(200, res)
            except Exception as e:
                log(f"push {action} failed: {e}")
                self._json_response(500, {"error": str(e)[:200]})
        elif path == "/api/login":
            body = self._read_json() or {}
            token = str(body.get("token", ""))
            if not AUTH_REQUIRED:
                return self._json_response(200, {"ok": True, "note": "auth disabled"})
            ok = (hmac.compare_digest(token, DESK_PASSWORD)
                  or hmac.compare_digest(token, POST_TOKEN))
            if not token or not ok:
                log(f"LOGIN FAIL from {self.address_string()}")
                # Deliberately vague: a specific message would confirm
                # whether a guessed token was close.
                return self._json_response(401, {"error": "invalid token"})
            data = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self._set_session_cookie(_make_session(), SESSION_DAYS * 86400)
            self.end_headers()
            self.wfile.write(data)
            log(f"LOGIN OK from {self.address_string()}")
        elif path == "/api/logout":
            data = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self._set_session_cookie("", 0)
            self.end_headers()
            self.wfile.write(data)
        elif path == "/api/auth/test":
            # Diagnostic endpoint: check if auth header is correct
            provided = self.headers.get("X-Saga-Token", "")
            return self._json_response(200, {
                "auth_required": AUTH_REQUIRED,
                "provided_token_matches": provided == POST_TOKEN and AUTH_REQUIRED,
            })
        elif path.startswith(f"/telegram/webhook/{TG_WEBHOOK_SECRET}"):
            # Telegram webhook — only callable with correct secret token
            self._handle_telegram_webhook()
        else:
            self._json_response(404, {"error": "not found", "path": path})

    # ─── Response helpers ────────────────────────────────────────────

    def _handle_telegram_webhook(self) -> None:
        """Receive a Telegram update, process /desk_* commands, optionally reply."""
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            update = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            log(f"TG webhook bad JSON: {e}")
            return self._json_response(400, {"error": "invalid JSON"})

        # Always 200 OK fast — Telegram won't retry if we take too long
        self._json_response(200, {"ok": True})

        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return
        text = msg.get("text", "")
        if not text or not text.startswith("/desk"):
            return  # not for us

        chat_id = msg.get("chat", {}).get("id")
        user = msg.get("from", {})
        username = user.get("username", "?")
        log(f"TG WEBHOOK from @{username}: {text[:80]}")

        try:
            self._process_telegram_command(chat_id, text)
        except Exception as e:
            log(f"TG handler exception: {e}")
            tg_send(chat_id, f"⚠️ Internal error: {e}")

    def _process_telegram_command(self, chat_id: int, text: str) -> None:
        """Dispatch a /desk_* command (assumes already validated prefix)."""
        parts = text.strip().split(None, 1)
        cmd_full = parts[0].lower()
        args = parts[1].split() if len(parts) > 1 else []

        if cmd_full in ("/desk_help", "/desk_help@putrihermes_bot"):
            tg_send(chat_id, TG_HELP_TEXT)
            return

        if cmd_full.startswith("/desk_status"):
            state = load_state()
            lines = ["📊 *Saga X Agent Desk Status*\n"]
            for aid in ("putri", "alisya", "julia", "farah", "delisha"):
                d = state.get(aid, {})
                emoji = TG_STATE_EMOJI.get(d.get("state", "?"), "•")
                lines.append(f"{emoji} *{d.get('name', aid)}* ({d.get('role', '?')}) — _{d.get('state', '?')}_")
                task = d.get("task", "")
                if task and task not in ("Idle", "Awaiting orders"):
                    lines.append(f"   └ {task[:80]}")
            tg_send(chat_id, "\n".join(lines))
            return

        if cmd_full.startswith("/desk_set"):
            if len(args) < 2:
                tg_send(chat_id, "❓ Usage: `/desk_set <agent> <state> [task]`")
                return
            agent = args[0].lower()
            new_state = args[1].lower()
            task = " ".join(args[2:]) if len(args) > 2 else ""
            if agent not in VALID_AGENTS:
                tg_send(chat_id, f"❌ Unknown agent. Valid: {', '.join(sorted(VALID_AGENTS))}")
                return
            if new_state not in VALID_STATES:
                tg_send(chat_id, f"❌ Invalid state. Valid: {', '.join(sorted(VALID_STATES))}")
                return
            set_agent(agent, new_state,
                      task or "Updated via Telegram", "telegram")
            log(f"TG STATE {agent} -> {new_state}")
            tg_send(chat_id, f"✅ {agent} → {new_state}\n{task or '(no task)'}")
            return

        if cmd_full.startswith("/desk_history"):
            n = 5
            if args:
                try:
                    n = min(int(args[0]), 50)
                except ValueError:
                    pass
            entries = read_history(n)["entries"]
            if not entries:
                tg_send(chat_id, "📭 No history yet.")
                return
            out = [f"📜 *Last {len(entries)} updates*\n"]
            for e in entries[:n]:
                ts = time.strftime("%H:%M", time.localtime(e["ts"]))
                tool = f" · `{e['tool']}`" if e.get("tool") else ""
                out.append(f"`{ts}` {e['agent']:8s} → {e['state']:9s}{tool}")
                out.append(f"   {e.get('task', '')[:80]}")
            tg_send(chat_id, "\n".join(out))
            return

        # Unknown /desk command
        tg_send(chat_id, TG_HELP_TEXT)

    def _authorised(self) -> bool:
        """Three ways in, all equivalent:

        - auth disabled (local development)
        - X-Saga-Token header (curl, desk.sh, cron)
        - a signed session cookie (the browser, after logging in)

        The browser gets a cookie rather than the raw token because a
        token in JavaScript is a token shipped to every visitor.
        """
        if not AUTH_REQUIRED:
            return True
        if hmac.compare_digest(self.headers.get("X-Saga-Token", ""), POST_TOKEN):
            return True
        return _valid_session(self._cookie("sagax_session"))

    def _cookie(self, name: str) -> str:
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            k, _, v = part.strip().partition("=")
            if k == name:
                return v
        return ""

    def _set_session_cookie(self, value: str, max_age: int) -> None:
        # Secure only over HTTPS, or a local http session could never
        # hold a cookie at all. nginx passes the real scheme through.
        proto = self.headers.get("X-Forwarded-Proto", "http")
        secure = "; Secure" if proto == "https" else ""
        self.send_header(
            "Set-Cookie",
            f"sagax_session={value}; HttpOnly; Path=/; SameSite=Strict"
            f"{secure}; Max-Age={max_age}")

    def _read_json(self) -> dict | None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            parsed = json.loads(raw.decode("utf-8") or "{}")
            return parsed if isinstance(parsed, dict) else None
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _json_response(self, code: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        # Same-origin: server.py serves both the page and the API, so no
        # CORS header is needed. `*` let any site on the internet read
        # this desk's state — fine for a public dashboard, not fine once
        # invoices and client records live behind it. Opt in explicitly
        # via CORS_ALLOWED_ORIGINS if a separate frontend ever appears.
        _origin = self.headers.get("Origin", "")
        if _origin and _origin in CORS_ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", _origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        # Only write body for GET/POST. For HEAD, headers-only is correct.
        if self.command != "HEAD":
            self.wfile.write(data)

    def _serve_file(self, path: Path, content_type: str, send_body: bool = True) -> None:
        if not path.is_file():
            self._json_response(404, {"error": "file missing", "path": str(path)})
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if send_body:
            self.wfile.write(data)

    def _serve_static(self, url_path: str, send_body: bool = True) -> None:
        rel = url_path[len("/static/"):]
        # Prevent path traversal
        if ".." in rel or rel.startswith("/"):
            self._json_response(400, {"error": "bad path"})
            return
        path = ROOT / "static" / rel
        if not path.is_file():
            self._json_response(404, {"error": "asset missing", "path": rel})
            return
        ext = path.suffix.lower()
        ctype = CONTENT_TYPES.get(ext, "application/octet-stream")
        self._serve_file(path, ctype, send_body)


SERVER_START = time.time()


def main() -> None:
    # Localhost by default. The old 0.0.0.0 default served the desk to
    # every device on the WiFi — harmless for a status board, not once
    # an API key and client records sit behind it. Production sets
    # HOST=0.0.0.0 explicitly in the systemd unit, behind nginx.
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    log(f"Starting Saga X Desk Dashboard on http://{host}:{port}")
    log(f"State file: {STATE_FILE}")
    httpd = ThreadingHTTPServer((host, port), Handler)
    log("Ready. Open the URL in a browser.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("Shutting down.")
        httpd.shutdown()


if __name__ == "__main__":
    main()
