"""
Saga X Agent Desk — agent state, backed by Postgres
===================================================
Replaces api/state.json and api/history.jsonl as the source of truth,
while keeping the exact response shapes that /api/state and
/api/history already return. The dashboard and the Telegram bot must
not be able to tell the difference.

Degradation matters here. The desk has been up for days and Abang uses
it; making it hard-fail on a Supabase hiccup would be a downgrade. So:

    read   -> Postgres, falling back to the state.json mirror
    write  -> Postgres, then mirror to state.json

The mirror is never authoritative. It exists so a database outage
shows slightly stale state instead of a broken page.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from . import config, db

ROOT = Path(__file__).resolve().parent.parent
STATE_MIRROR = ROOT / "api" / "state.json"
LEGACY_HISTORY = ROOT / "api" / "history.jsonl"

# The exact key order the dashboard has always received.
_FIELDS = ("name", "role", "state", "task", "current_tool", "updated_at")


def _row_to_legacy(row: dict) -> dict:
    return {
        "name": row.get("name"),
        "role": row.get("role"),
        "state": row.get("state") or "idle",
        "task": row.get("task") or "",
        "current_tool": row.get("current_tool"),
        "updated_at": row.get("updated_at"),
    }


def _write_mirror(state: dict) -> None:
    """Atomic, same tmp+rename pattern the original server used."""
    try:
        STATE_MIRROR.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_MIRROR.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        tmp.replace(STATE_MIRROR)
    except OSError:
        pass  # the mirror is a convenience, never a hard dependency


def _read_mirror() -> dict:
    try:
        with STATE_MIRROR.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def load_state() -> dict:
    """All agents, in the legacy shape. Falls back to the mirror if the
    database is unreachable, so the dashboard degrades to stale rather
    than to an error page."""
    try:
        rows = db.select("agent_state", order="agent asc")
    except Exception:
        mirror = _read_mirror()
        if mirror:
            return mirror
        raise

    state = {}
    for aid in config.AGENTS:  # fixed order, not whatever the DB returns
        row = next((r for r in rows if r["agent"] == aid), None)
        if row:
            state[aid] = _row_to_legacy(row)
        else:
            name, role = config.AGENT_ROLES.get(aid, (aid.title(), "?"))
            state[aid] = {"name": name, "role": role, "state": "offline",
                          "task": "not seeded", "current_tool": None,
                          "updated_at": None}
    _write_mirror(state)
    return state


def set_state(agent_id: str, new_state: str, task: str = "",
              current_tool: str | None = None) -> dict:
    """Update one agent and append to history. Returns the agent's row
    in the legacy shape, which is what POST /api/state echoes back."""
    if agent_id not in config.AGENTS:
        raise ValueError(f"unknown agent: {agent_id}")
    if new_state not in config.VALID_STATES:
        raise ValueError(f"invalid state: {new_state}")

    now = int(time.time())
    task = str(task)[:200]

    rows = db.update("agent_state", {"agent": agent_id}, {
        "state": new_state,
        "task": task,
        "current_tool": current_tool,
        "updated_at": now,
    })
    if not rows:
        raise ValueError(f"agent_state row missing for {agent_id}")

    # History is best-effort: a failure here must not lose the state
    # change that already committed.
    try:
        db.insert("state_history", {
            "agent": agent_id, "state": new_state,
            "task": task, "tool": current_tool, "ts": now,
        })
    except Exception:
        pass

    _write_mirror(load_state_uncached())
    return _row_to_legacy(rows[0])


def load_state_uncached() -> dict:
    """load_state() without the mirror write, to avoid recursing."""
    rows = db.select("agent_state", order="agent asc")
    out = {}
    for aid in config.AGENTS:
        row = next((r for r in rows if r["agent"] == aid), None)
        if row:
            out[aid] = _row_to_legacy(row)
    return out


def history(limit: int = 100) -> dict:
    """Newest first, in the shape /api/history already returns."""
    limit = max(1, min(int(limit), 1000))
    rows = db.select("state_history", columns="ts,agent,state,task,tool",
                     order="ts desc", limit=limit)
    entries = [{"ts": r["ts"], "agent": r["agent"], "state": r["state"],
                "task": r["task"] or "", "tool": r["tool"]} for r in rows]
    return {"entries": entries, "count": len(entries)}


# ── One-time import from the files this replaces ────────────────

def import_legacy(dry_run: bool = True) -> dict[str, Any]:
    """Seed Postgres from the live api/state.json and history.jsonl.

    Production has days of real state; starting the tables empty would
    throw it away. Safe to re-run — state is upserted by agent, and
    history rows are skipped when an identical (agent, ts) already
    exists.
    """
    report: dict[str, Any] = {"states": 0, "history": 0, "skipped": 0,
                              "dry_run": dry_run}

    mirror = _read_mirror()
    for aid, data in mirror.items():
        if aid not in config.AGENTS:
            report["skipped"] += 1
            continue
        report["states"] += 1
        if not dry_run:
            name, role = config.AGENT_ROLES.get(aid, (aid.title(), "?"))
            db.upsert("agent_state", {
                "agent": aid,
                "name": data.get("name") or name,
                "role": data.get("role") or role,
                "state": data.get("state") or "idle",
                "task": (data.get("task") or "")[:200],
                "current_tool": data.get("current_tool"),
                "updated_at": data.get("updated_at"),
            }, conflict="agent")

    if LEGACY_HISTORY.is_file():
        seen: set[tuple] = set()
        if not dry_run:
            for r in db.select("state_history", columns="agent,ts"):
                seen.add((r["agent"], r["ts"]))
        with LEGACY_HISTORY.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    report["skipped"] += 1
                    continue
                if e.get("agent") not in config.AGENTS or not e.get("ts"):
                    report["skipped"] += 1
                    continue
                if (e["agent"], e["ts"]) in seen:
                    report["skipped"] += 1
                    continue
                report["history"] += 1
                if not dry_run:
                    db.insert("state_history", {
                        "agent": e["agent"],
                        "state": e.get("state") or "idle",
                        "task": (e.get("task") or "")[:200],
                        "tool": e.get("tool"),
                        "ts": int(e["ts"]),
                    })
                    seen.add((e["agent"], e["ts"]))
    return report
