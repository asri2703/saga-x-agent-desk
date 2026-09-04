#!/usr/bin/env python3
"""
Telegram Bridge — Saga X Agent Desk
====================================
Long-polling bridge that lets Abang update agent states via Telegram chat.
Uses the existing @putrihermes_bot token, but only reacts to commands
prefixed with /desk_ to avoid conflict with other bot users.

Commands:
  /desk_status                  → Show all 5 agents current state
  /desk_set <agent> <state> [task]  → Update one agent's state
  /desk_history [N]             → Show last N updates
  /desk_help                    → List commands

States:  idle, thinking, working, done, error, offline
Agents:  putri, alisya, julia, farah, delisha

Configuration (env vars):
  TG_BOT_TOKEN     (required)
  DESK_URL         (default https://desk.sagaxventures.com)
  DESK_TOKEN       (required for write ops; falls back to POST_TOKEN)
  TG_ALLOWED_USERS (optional comma-separated list of telegram user IDs;
                    if empty, accepts all messages — INSECURE for prod)
"""

import json
import logging
import os
import signal
import sys
import time
import urllib.request
import urllib.error

TG_API = "https://api.telegram.org"
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
DESK_URL = os.environ.get("DESK_URL", "https://desk.sagaxventures.com")
DESK_TOKEN = os.environ.get("DESK_TOKEN", "") or os.environ.get("POST_TOKEN", "")
TG_ALLOWED = [x.strip() for x in os.environ.get("TG_ALLOWED_USERS", "").split(",") if x.strip()]

VALID_AGENTS = {"putri", "alisya", "julia", "farah", "delisha"}
VALID_STATES = {"idle", "thinking", "working", "done", "error", "offline"}
COMMAND_PREFIX = "/desk"

LOG_FILE = os.environ.get("LOG_FILE", "/opt/saga-x-desk/logs/telegram_bridge.log")


def log(msg: str) -> None:
    """Append-only log + stdout."""
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass
    print(line, flush=True)


def tg_api(method: str, params: dict | None = None, timeout: int = 30) -> dict:
    """Call Telegram Bot API. Long-poll uses long timeout."""
    url = f"{TG_API}/bot{TG_BOT_TOKEN}/{method}"
    if params is None:
        params = {}
    data = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "SagaXDeskBridge/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        log(f"TG API error: {method}: {e}")
        return {"ok": False, "error": str(e)}


def desk_api(method: str, path: str, body: dict | None = None) -> dict:
    """Call Saga X desk API."""
    url = f"{DESK_URL}{path}"
    headers = {
        "User-Agent": "SagaXDeskBridge/1.0",
        "Accept-Language": "en-US,en;q=0.9",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if method == "POST" and DESK_TOKEN:
        headers["X-Saga-Token"] = DESK_TOKEN

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        log(f"Desk API error: {method} {path}: {e}")
        return {"error": str(e)}


def send_message(chat_id: int, text: str, parse_mode: str | None = "Markdown") -> bool:
    """Reply to Telegram chat."""
    result = tg_api("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    })
    if not result.get("ok"):
        log(f"sendMessage failed: {result}")
    return result.get("ok", False)


def is_authorized(user_id: int) -> bool:
    """Check if user is allowed to issue commands. Empty list = allow all (DEV ONLY)."""
    if not TG_ALLOWED:
        return True  # dev mode
    return str(user_id) in TG_ALLOWED


def handle_command(chat_id: int, user_id: int, text: str) -> None:
    """Parse and dispatch a command."""
    if not is_authorized(user_id):
        log(f"UNAUTHORIZED command from user_id={user_id}")
        send_message(chat_id, "⛔ You are not authorized to use this bot.")
        return

    parts = text.strip().split(None, 1)
    if len(parts) < 1:
        return
    cmd_full = parts[0].lower()
    args_str = parts[1] if len(parts) > 1 else ""
    args = args_str.split() if args_str else []

    # /desk_help or /desk_help@botname
    if cmd_full.startswith(f"{COMMAND_PREFIX}_help"):
        send_message(chat_id, HELP_TEXT)
        return

    if cmd_full.startswith(f"{COMMAND_PREFIX}_status"):
        state = desk_api("GET", "/api/state")
        if "error" in state:
            send_message(chat_id, f"❌ Desk API error: {state['error']}")
            return
        lines = ["📊 *Saga X Agent Desk Status*\n"]
        for aid in ("putri", "alisya", "julia", "farah", "delisha"):
            d = state.get(aid, {})
            emoji = STATE_EMOJI.get(d.get("state", "?"), "•")
            lines.append(f"{emoji} *{d.get('name', aid)}* ({d.get('role', '?')}) — _{d.get('state', '?')}_")
            task = d.get("task", "")
            if task and task not in ("Idle", "Awaiting orders"):
                lines.append(f"   └ {task[:80]}")
        send_message(chat_id, "\n".join(lines))
        return

    if cmd_full.startswith(f"{COMMAND_PREFIX}_set"):
        if len(args) < 2:
            send_message(chat_id, "❓ Usage: `/desk_set <agent> <state> [task]`")
            return
        agent = args[0].lower()
        state_name = args[1].lower()
        task = " ".join(args[2:]) if len(args) > 2 else ""
        if agent not in VALID_AGENTS:
            send_message(chat_id, f"❌ Unknown agent. Valid: {', '.join(sorted(VALID_AGENTS))}")
            return
        if state_name not in VALID_STATES:
            send_message(chat_id, f"❌ Invalid state. Valid: {', '.join(sorted(VALID_STATES))}")
            return

        result = desk_api("POST", "/api/state", {
            "agent_id": agent,
            "state": state_name,
            "task": task or f"Updated via Telegram",
            "current_tool": "telegram",
        })
        if result.get("ok"):
            send_message(chat_id, f"✅ {agent} → {state_name}\n{task or '(no task)'}")
        else:
            err = result.get("error", "unknown")
            send_message(chat_id, f"❌ Update failed: {err}\n💡 Token may be expired. See `/desk_status` to verify.")
        return

    if cmd_full.startswith(f"{COMMAND_PREFIX}_history"):
        n = 5
        if args:
            try:
                n = min(int(args[0]), 50)
            except ValueError:
                pass
        result = desk_api("GET", f"/api/history?limit={n}")
        entries = result.get("entries", [])
        if not entries:
            send_message(chat_id, "📭 No history yet.")
            return
        lines = [f"📜 *Last {len(entries)} updates*\n"]
        for e in entries[:n]:
            ts = time.strftime("%H:%M", time.localtime(e["ts"]))
            tool = f" · `{e['tool']}`" if e.get("tool") else ""
            lines.append(f"`{ts}` {e['agent']:8s} → {e['state']:9s}{tool}")
            lines.append(f"   {e.get('task', '')[:80]}")
        send_message(chat_id, "\n".join(lines))
        return

    # Unknown command — ignore silently (don't reply to noise)
    log(f"Ignored unknown command: {cmd_full}")


STATE_EMOJI = {
    "idle": "💤",
    "thinking": "💭",
    "working": "⚡",
    "done": "✅",
    "error": "❌",
    "offline": "⚫",
}

HELP_TEXT = """🤖 *Saga X Agent Desk Bot*

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


_running = True


def shutdown(signum, frame):
    global _running
    log(f"Received signal {signum}, shutting down...")
    _running = False


def main() -> int:
    if not TG_BOT_TOKEN:
        log("FATAL: TG_BOT_TOKEN not set")
        return 2

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # Verify bot is reachable
    me = tg_api("getMe", timeout=15)
    if not me.get("ok"):
        log(f"FATAL: bot getMe failed: {me}")
        return 2
    bot = me["result"]
    log(f"Bot @{bot.get('username')} (id={bot.get('id')}) — bridging started")

    offset = 0
    idle_polls = 0
    while _running:
        try:
            updates = tg_api("getUpdates", {
                "offset": offset,
                "timeout": 25,  # long-poll
                "allowed_updates": ["message"],
            }, timeout=30)
        except Exception as e:
            log(f"getUpdates exception: {e}")
            time.sleep(5)
            continue

        if not updates.get("ok"):
            time.sleep(2)
            continue

        result = updates.get("result", [])
        if not result:
            idle_polls += 1
            if idle_polls % 100 == 0:
                log(f"Heartbeat: {idle_polls} idle polls")
            continue

        idle_polls = 0
        for upd in result:
            offset = max(offset, upd["update_id"] + 1)
            msg = upd.get("message")
            if not msg:
                continue
            text = msg.get("text", "")
            chat = msg.get("chat", {})
            user = msg.get("from", {})
            chat_id = chat.get("id")
            user_id = user.get("id")
            username = user.get("username", "?")
            if not text.startswith(COMMAND_PREFIX):
                continue  # ignore non-desk messages
            log(f"CMD from @{username} (id={user_id}): {text[:80]}")
            try:
                handle_command(chat_id, user_id, text)
            except Exception as e:
                log(f"Handler exception: {e}")
                send_message(chat_id, f"⚠️ Internal error: {e}")

    log("Stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
