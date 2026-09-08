"""
Saga X Agent Desk — Mastery Signal webhook client
=================================================
Reads the Flask receiver that runs alongside the Mastery automation:
cron health, live signal counts, state-file integrity. It was built to
be polled by "the CTO virtual office" — that is Alisya.

Endpoints (`X-CTO-Key` header on all but /health):

    GET /health        liveness, no auth
    GET /status        alerts + summary
    GET /api/cron      every cron, last run, last status
    GET /api/signals   live active signals from Supabase
    GET /api/state     24 state files, size/mtime/ok

Network note: the receiver binds 0.0.0.0:5002 on the *old* server, but
that port is firewalled, so nothing outside can reach it — including
this desk. Every call here degrades to a clear "unreachable" rather
than an exception, so Alisya can say the monitor is blind instead of
appearing to have checked.

Reading this is the whole integration. There is no tool here that
changes anything on the Mastery side, deliberately: that bot is live
revenue and this desk only watches it.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from . import config

TIMEOUT = 12


def configured() -> bool:
    return bool(config.get("MASTERY_WEBHOOK_URL") and config.get("CTO_API_KEY"))


def _get(path: str, auth: bool = True) -> dict[str, Any]:
    base = config.get("MASTERY_WEBHOOK_URL", "").rstrip("/")
    if not base:
        return {"ok": False, "error": "MASTERY_WEBHOOK_URL not set"}
    headers = {"User-Agent": "SagaXDesk/2.0"}
    if auth:
        key = config.get("CTO_API_KEY")
        if not key:
            return {"ok": False, "error": "CTO_API_KEY not set"}
        headers["X-CTO-Key"] = key
    try:
        req = urllib.request.Request(base + path, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read()
            return {"ok": True, "data": json.loads(body) if body else {}}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"ok": False, "error": "401 — CTO_API_KEY rejected"}
        return {"ok": False, "error": f"HTTP {e.code}"}
    except Exception as e:
        # Firewalled, host down, DNS — all the same to a caller who just
        # needs to know the check did not happen.
        return {"ok": False, "unreachable": True,
                "error": f"unreachable: {str(e)[:120]}"}


def health() -> dict:
    return _get("/health", auth=False)


def status() -> dict:
    return _get("/status")


def crons() -> dict:
    return _get("/api/cron")


def signals() -> dict:
    return _get("/api/signals")


def state_files() -> dict:
    return _get("/api/state")


def summary() -> dict:
    """One call for Alisya: is it up, and is anything wrong?

    Returns a flat shape whether or not the box is reachable, so the
    caller never has to guess which half of the response exists.
    """
    if not configured():
        return {"reachable": False, "configured": False,
                "note": "MASTERY_WEBHOOK_URL / CTO_API_KEY not set"}

    h = health()
    if not h.get("ok"):
        return {"reachable": False, "configured": True, "error": h.get("error"),
                "note": "Mastery webhook cannot be reached from this host. "
                        "Port 5002 on the Mastery server is firewalled; it "
                        "needs to allow this desk's IP."}

    s = status()
    if not s.get("ok"):
        return {"reachable": True, "authorised": False, "error": s.get("error")}

    d = s.get("data") or {}
    alerts = d.get("alerts") or []
    summ = d.get("summary") or {}
    return {
        "reachable": True,
        "authorised": True,
        "uptime_seconds": (h.get("data") or {}).get("uptime_seconds"),
        "alerts": alerts,
        "alert_count": len(alerts),
        "total_crons": summ.get("total_crons"),
        "enabled_crons": summ.get("enabled_crons"),
        "paused_crons": summ.get("paused_crons"),
        "active_signals": summ.get("active_signals"),
        # From the config Abang supplied: 0-5 is normal, 10+ means the
        # bot is misbehaving. Worth flagging rather than leaving him to
        # remember the range.
        "signals_note": (
            "unusually high — check the bot"
            if isinstance(summ.get("active_signals"), int)
            and summ["active_signals"] >= 10 else None),
    }
