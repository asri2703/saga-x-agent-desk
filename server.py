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

import json
import os
import sys
import time
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
AUTH_REQUIRED = os.environ.get("AUTH_REQUIRED", "0") == "1"

# Valid agent IDs (must match dashboard avatars)
VALID_AGENTS = {"putri", "alisya", "julia", "farah", "delisha"}

# Valid states
VALID_STATES = {"idle", "thinking", "working", "done", "error", "offline"}

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


def load_state() -> dict:
    """Load state from disk, falling back to defaults on corruption."""
    if not STATE_FILE.exists():
        save_state(DEFAULT_STATE)
        return DEFAULT_STATE
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            state = json.load(f)
        # Backfill any missing agents
        for k, v in DEFAULT_STATE.items():
            state.setdefault(k, v)
        return state
    except (json.JSONDecodeError, OSError) as e:
        log(f"State corrupt, resetting: {e}")
        save_state(DEFAULT_STATE)
        return DEFAULT_STATE


def save_state(state: dict) -> None:
    """Atomic write — write to .tmp then rename to avoid partial reads."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    tmp.replace(STATE_FILE)


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
            entries = []
            if HISTORY_FILE.exists():
                try:
                    with HISTORY_FILE.open("r", encoding="utf-8") as f:
                        # Read last N lines efficiently
                        lines = f.readlines()[-limit:]
                        for line in reversed(lines):
                            try:
                                entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
                except OSError as e:
                    log(f"history read failed: {e}")
            self._json_response(200, {"entries": entries, "count": len(entries)})
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

            # Update atomically
            state = load_state()
            state[agent_id]["state"] = new_state
            state[agent_id]["task"] = str(payload.get("task", ""))[:200]
            state[agent_id]["current_tool"] = payload.get("current_tool")
            state[agent_id]["updated_at"] = int(time.time())
            save_state(state)

            # Append to history log (append-only, one JSON object per line)
            try:
                HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
                with HISTORY_FILE.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "ts": state[agent_id]["updated_at"],
                        "agent": agent_id,
                        "state": new_state,
                        "task": state[agent_id]["task"],
                        "tool": state[agent_id]["current_tool"],
                    }, ensure_ascii=False) + "\n")
            except OSError as e:
                log(f"history append failed: {e}")

            log(f"STATE {agent_id} -> {new_state} task={state[agent_id]['task']!r}")
            self._json_response(200, {"ok": True, "agent_id": agent_id, "state": state[agent_id]})
        elif path == "/api/auth/test":
            # Diagnostic endpoint: check if auth header is correct
            provided = self.headers.get("X-Saga-Token", "")
            return self._json_response(200, {
                "auth_required": AUTH_REQUIRED,
                "provided_token_matches": provided == POST_TOKEN and AUTH_REQUIRED,
            })
        else:
            self._json_response(404, {"error": "not found", "path": path})

    # ─── Response helpers ────────────────────────────────────────────

    def _json_response(self, code: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
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
    host = os.environ.get("HOST", "0.0.0.0")
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
