"""
Saga X Agent Desk — Alisya's monitoring
=======================================
Replaces scripts/domain_watch.py. Three things that one got wrong:

  1. It watched 2 of 5 properties. space.sagaxventures.com,
     masterysignal.com and the desk itself were unmonitored.
  2. It reported "✅ 1 domains healthy" with state `idle` while
     saga-x-crm.com was failing DNS entirely. A green tick over a dead
     domain is worse than no monitoring, because it buys false calm.
  3. It told nobody. Nothing opened, nothing pinged.

Design rules:

  * Alisya never fixes anything. She detects, records, and notifies.
    `incidents.suggested_action` is where she writes what she *would*
    do; Abang decides. There is deliberately no remediation path.
  * State must be honest. If anything is down, Alisya's state says so.
    The summary can never claim health it has not verified.
  * A monitor must fail `fail_threshold` times in a row before an
    incident opens, so a single blip does not wake anyone at 3am.

Run from cron:  python -m agents.monitors
"""

from __future__ import annotations

import socket
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from . import config, db, state

# Cloudflare returns 403 to urllib's default User-Agent. Verified on
# desk.sagaxventures.com and masterysignal.com — without this header
# Alisya would invent outages on the two proxied domains.
USER_AGENT = "SagaXDeskMonitor/2.0 (+https://desk.sagaxventures.com)"
TIMEOUT = 12


# ── Checking ────────────────────────────────────────────────────

def check_https(target: str) -> dict[str, Any]:
    """DNS + TLS + HTTP in one pass. Returns a monitor_checks row."""
    out: dict[str, Any] = {
        "ok": False, "http_status": None, "response_ms": None,
        "ssl_days_left": None, "resolved_ip": None, "error": None,
    }
    started = time.time()

    # getaddrinfo, not gethostbyname — the latter is IPv4-only, and
    # several of these domains resolve to IPv6 behind Cloudflare.
    try:
        infos = socket.getaddrinfo(target, 443, proto=socket.IPPROTO_TCP)
        out["resolved_ip"] = infos[0][4][0]
    except socket.gaierror as e:
        out["error"] = f"DNS failed: {e}"
        return out

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((target, 443), timeout=TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=target) as ssock:
                cert = ssock.getpeercert()
        if cert and cert.get("notAfter"):
            expiry = datetime.strptime(
                cert["notAfter"], "%b %d %H:%M:%S %Y %Z"
            ).replace(tzinfo=timezone.utc)
            out["ssl_days_left"] = (expiry - datetime.now(timezone.utc)).days
    except (ssl.SSLError, socket.timeout, OSError) as e:
        out["error"] = f"TLS failed: {e}"
        return out

    try:
        req = urllib.request.Request(
            f"https://{target}/", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            out["http_status"] = r.status
            out["ok"] = 200 <= r.status < 400
    except urllib.error.HTTPError as e:
        out["http_status"] = e.code
        # 4xx means the server answered; only 5xx counts as down.
        out["ok"] = e.code < 500
        if not out["ok"]:
            out["error"] = f"HTTP {e.code}"
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        out["error"] = f"HTTP failed: {e}"
        return out

    out["response_ms"] = int((time.time() - started) * 1000)
    return out


def check_dns(target: str) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "http_status": None, "response_ms": None,
                           "ssl_days_left": None, "resolved_ip": None, "error": None}
    started = time.time()
    try:
        infos = socket.getaddrinfo(target, None)
        out["resolved_ip"] = infos[0][4][0]
        out["ok"] = True
        out["response_ms"] = int((time.time() - started) * 1000)
    except socket.gaierror as e:
        out["error"] = f"DNS failed: {e}"
    return out


CHECKERS = {"https": check_https, "dns": check_dns, "ssl": check_https}


# ── Incident handling ───────────────────────────────────────────

def _consecutive_failures(monitor_id: str, limit: int = 10) -> int:
    rows = db.select("monitor_checks", filters={"monitor_id": monitor_id},
                     columns="ok", order="checked_at desc", limit=limit)
    n = 0
    for r in rows:
        if r["ok"]:
            break
        n += 1
    return n


def _open_incident(monitor: dict, result: dict, failures: int) -> dict | None:
    """Open one incident per monitor, or leave the existing one alone."""
    existing = db.select("incidents",
                         filters={"monitor_id": monitor["id"],
                                  "status": ("in", ["open", "acknowledged"])},
                         limit=1)
    if existing:
        return None

    target = monitor["target"]
    err = result.get("error") or f"HTTP {result.get('http_status')}"
    critical = monitor["target"] in ("masterysignal.com", "desk.sagaxventures.com")

    incident = db.insert("incidents", {
        "monitor_id": monitor["id"],
        "title": f"{monitor['name']} is down",
        "detail": f"{target}: {err} ({failures} consecutive checks)",
        "severity": "critical" if critical else "warning",
        "status": "open",
        # Alisya proposes. She has no mechanism to act on this.
        "suggested_action": _suggest(monitor, result),
    })
    return incident


def _suggest(monitor: dict, result: dict) -> str:
    err = (result.get("error") or "").lower()
    if "dns" in err:
        return (f"Check DNS for {monitor['target']} in Cloudflare. If the domain "
                f"is no longer used, disable this monitor rather than leaving it "
                f"failing.")
    if "tls" in err or "ssl" in err:
        return f"Certificate problem on {monitor['target']}. Check certbot renewal."
    if result.get("http_status") and result["http_status"] >= 500:
        return f"{monitor['target']} returned {result['http_status']}. Check the origin server and its logs."
    return f"{monitor['target']} unreachable. Check the host is up and nginx is running."


def _resolve_incident(monitor: dict) -> dict | None:
    open_ones = db.select("incidents",
                          filters={"monitor_id": monitor["id"],
                                   "status": ("in", ["open", "acknowledged"])},
                          limit=1)
    if not open_ones:
        return None
    inc = open_ones[0]
    # A real datetime, not the string "now()" — passed as a parameter
    # that would be stored literally rather than evaluated.
    db.update("incidents", {"id": inc["id"]},
              {"status": "resolved",
               "resolved_at": datetime.now(timezone.utc)})
    return inc


def _notify(incident: dict, body: str, title: str) -> None:
    """Queue only. The sender runs on the VPS, where the bot token is."""
    try:
        db.insert("notifications", {
            "incident_id": incident["id"], "agent": "alisya",
            "channel": "telegram", "title": title, "body": body,
        })
    except Exception:
        pass


# ── The run ─────────────────────────────────────────────────────

def run_all() -> dict[str, Any]:
    monitors = db.select("monitors", filters={"enabled": True}, order="name asc")
    if not monitors:
        state.set_state("alisya", "error", "No monitors configured", "monitor")
        return {"checked": 0, "down": [], "opened": 0, "resolved": 0}

    state.set_state("alisya", "working",
                    f"Checking {len(monitors)} properties", "monitor")

    down: list[str] = []
    warnings: list[str] = []
    times: list[int] = []
    opened = resolved = 0

    for m in monitors:
        checker = CHECKERS.get(m["kind"], check_https)
        result = checker(m["target"])

        try:
            db.insert("monitor_checks", {
                "monitor_id": m["id"], "ok": result["ok"],
                "http_status": result["http_status"],
                "response_ms": result["response_ms"],
                "ssl_days_left": result["ssl_days_left"],
                "resolved_ip": result["resolved_ip"],
                "error": result["error"],
            })
        except Exception:
            pass

        if result["response_ms"]:
            times.append(result["response_ms"])

        if result["ok"]:
            inc = _resolve_incident(m)
            if inc:
                resolved += 1
                _notify(inc, f"✅ {m['name']} ({m['target']}) is back up.",
                        f"Recovered: {m['name']}")
            days = result.get("ssl_days_left")
            if days is not None and days < (m.get("warn_days_left") or 14):
                warnings.append(f"{m['target']} SSL {days}d")
        else:
            down.append(m["target"])
            failures = _consecutive_failures(m["id"])
            if failures >= (m.get("fail_threshold") or 2):
                inc = _open_incident(m, result, failures)
                if inc:
                    opened += 1
                    _notify(inc,
                            f"⚠️ {m['name']} is down.\n"
                            f"{m['target']}: {result.get('error') or result.get('http_status')}\n\n"
                            f"Suggested: {inc['suggested_action']}\n\n"
                            f"I have not changed anything.",
                            f"Down: {m['name']}")
                    # Wake any assignment waiting on this event. Best
                    # effort — a scheduling failure must not cost us the
                    # monitoring result we already recorded.
                    try:
                        from . import scheduler
                        scheduler.fire_event("monitor_down",
                                             detail=str(inc["id"]))
                    except Exception as e:
                        pass

    # Honest state. This is the bug from the old script: it must not be
    # possible to report a tick while something is failing.
    avg = int(sum(times) / len(times)) if times else 0
    healthy = len(monitors) - len(down)
    if down:
        summary = f"⚠️ {len(down)} down: {', '.join(down[:2])}"
        if len(down) > 2:
            summary += f" +{len(down) - 2}"
        summary += f" · {healthy}/{len(monitors)} healthy"
        state.set_state("alisya", "error", summary[:200], "monitor")
    elif warnings:
        state.set_state("alisya", "idle",
                        f"⚠️ {'; '.join(warnings[:2])} · {healthy}/{len(monitors)} up"[:200],
                        "monitor")
    else:
        state.set_state("alisya", "idle",
                        f"✅ {healthy}/{len(monitors)} healthy, avg {avg}ms", "monitor")

    return {"checked": len(monitors), "down": down, "warnings": warnings,
            "opened": opened, "resolved": resolved, "avg_ms": avg}


if __name__ == "__main__":
    report = run_all()
    print(f"checked  : {report['checked']}")
    print(f"down     : {report['down'] or 'none'}")
    print(f"warnings : {report.get('warnings') or 'none'}")
    print(f"incidents: +{report['opened']} opened, {report['resolved']} resolved")
    print(f"avg      : {report['avg_ms']}ms")
