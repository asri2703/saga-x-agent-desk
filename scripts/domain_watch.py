#!/usr/bin/env python3
"""
DomainWatch — Saga X Infrastructure Monitor
==========================================
Periodically checks domain health (HTTP status, SSL cert, response time)
and updates Alisya's (CTO) agent state on the desk dashboard.

Run from cron every 6h:
  0 */6 * * * /opt/saga-x-desk/scripts/domain_watch.py

Environment:
  DESK_URL     (default https://desk.sagaxventures.com)
  DESK_TOKEN   (required — from /etc/saga-x-desk/post-token.env)
  DOMAINS      (default "sagaxventures.com,saga-x-crm.com")

Exit codes:
  0 = all checks passed
  1 = one or more domains have issues
  2 = script error (config / network)
"""

import os
import ssl
import socket
import time
import json
import urllib.request
import urllib.error
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DESK_URL = os.environ.get("DESK_URL", "https://desk.sagaxventures.com")
# Accept either DESK_TOKEN (direct) or POST_TOKEN (from systemd-style env file)
DESK_TOKEN = os.environ.get("DESK_TOKEN", "") or os.environ.get("POST_TOKEN", "")
DOMAINS = os.environ.get("DOMAINS", "sagaxventures.com,saga-x-crm.com").split(",")
CHECK_TIMEOUT = int(os.environ.get("CHECK_TIMEOUT", "10"))

LOG_FILE = Path("/opt/saga-x-desk/logs/domain_watch.log") if Path("/opt/saga-x-desk/logs").exists() else Path("/tmp/domain_watch.log")


def log(msg: str) -> None:
    """Append log with timestamp."""
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n"
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a") as f:
            f.write(line)
    except OSError:
        pass
    sys.stdout.write(line)
    sys.stdout.flush()


def check_domain(domain: str) -> dict:
    """
    Check domain health:
    - DNS resolution
    - HTTPS reachability (HTTP 2xx/3xx)
    - SSL cert validity + days remaining
    - Response time
    Returns a dict with all results.
    """
    result = {
        "domain": domain,
        "dns_ok": False,
        "dns_ip": None,
        "https_ok": False,
        "http_status": None,
        "http_time_ms": None,
        "ssl_ok": False,
        "ssl_days_left": None,
        "ssl_expiry": None,
        "error": None,
    }

    # 1. DNS resolution
    try:
        ip = socket.gethostbyname(domain)
        result["dns_ok"] = True
        result["dns_ip"] = ip
    except socket.gaierror as e:
        result["error"] = f"DNS fail: {e}"
        return result

    # 2. HTTPS + SSL check (single connection)
    start = time.time()
    ctx = ssl.create_default_context()
    try:
        conn = socket.create_connection((domain, 443), timeout=CHECK_TIMEOUT)
        with ctx.wrap_socket(conn, server_hostname=domain) as ssock:
            cert_bin = ssock.getpeercert(binary_form=False)
            if cert_bin is None:
                raise ssl.SSLError("No certificate returned")
            cert = cert_bin
            ssl_ok = True
            # Parse expiry
            expiry_str = str(cert.get("notAfter", "") or "")
            if expiry_str:
                # Format: 'Sep  4 14:21:37 2026 GMT' — handle single-digit day
                try:
                    expiry_dt = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                except ValueError:
                    expiry_dt = datetime.strptime(expiry_str, "%b  %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                days_left = (expiry_dt - datetime.now(timezone.utc)).days
                result["ssl_expiry"] = expiry_str
                result["ssl_days_left"] = days_left
                result["ssl_ok"] = days_left > 0
        conn.close()
    except (socket.timeout, ConnectionRefusedError, ssl.SSLError, OSError) as e:
        result["error"] = f"HTTPS/SSL fail: {e}"
        return result

    # 3. HTTP request (response code + timing)
    try:
        req = urllib.request.Request(f"https://{domain}/", method="GET",
                                     headers={"User-Agent": "SagaXDomainWatch/1.0"})
        with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT) as r:
            result["http_status"] = r.status
            result["https_ok"] = 200 <= r.status < 400
    except urllib.error.HTTPError as e:
        # 4xx/5xx with reachable server = "not 200 but up"
        result["http_status"] = e.code
        result["https_ok"] = e.code < 500  # 4xx means server up but path issue
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        result["error"] = f"HTTP fail: {e}"
        return result

    result["http_time_ms"] = int((time.time() - start) * 1000)
    return result


def build_task_summary(results: list) -> tuple:
    """
    Build a short task description for Alisya's state.
    Returns (state, task_summary, tool_name).
    """
    if not results:
        return ("error", "No domains configured", "monitor")

    # Aggregate health
    all_ok = all(r["https_ok"] and r["ssl_ok"] and r["dns_ok"] for r in results)
    ssl_warnings = [r for r in results if r.get("ssl_days_left") is not None and r["ssl_days_left"] < 30]
    down_domains = [r["domain"] for r in results if not r["https_ok"] or not r["dns_ok"]]

    if down_domains:
        state = "error"
        summary = f"❌ DOWN: {', '.join(down_domains)}"
    elif ssl_warnings:
        state = "thinking"
        names = [f"{r['domain']}({r['ssl_days_left']}d)" for r in ssl_warnings]
        summary = f"⚠️ SSL expiring: {', '.join(names)}"
    else:
        state = "idle"
        avg_ms = sum(r.get("http_time_ms", 0) for r in results) // max(len(results), 1)
        summary = f"✅ {len(results)} domains healthy, avg {avg_ms}ms"

    return (state, summary, "domain_watch")


def update_alisya(state: str, task: str, tool: str = "domain_watch") -> bool:
    """POST state update for Alisya via dashboard API."""
    if not DESK_TOKEN:
        log("ERROR: DESK_TOKEN not set, cannot update Alisya state")
        return False

    payload = json.dumps({
        "agent_id": "alisya",
        "state": state,
        "task": task,
        "current_tool": tool,
    }).encode()

    req = urllib.request.Request(
        f"{DESK_URL}/api/state",
        method="POST",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Saga-Token": DESK_TOKEN,
            "User-Agent": "SagaXDomainWatch/1.0",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = json.loads(r.read())
            log(f"State updated: alisya -> {state} | {task}")
            return body.get("ok") is True
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        log(f"State update failed: {e}")
        return False


def main() -> int:
    log(f"DomainWatch run started for {len(DOMAINS)} domain(s)")
    results = []
    for domain in DOMAINS:
        domain = domain.strip()
        if not domain:
            continue
        log(f"Checking {domain}...")
        result = check_domain(domain)
        results.append(result)
        log(f"  DNS={result['dns_ok']} HTTPS={result['https_ok']} SSL={result['ssl_ok']}"
            f" status={result['http_status']} time={result.get('http_time_ms')}ms"
            f" ssl_days={result.get('ssl_days_left')}"
            f" err={result['error']}")

    state, task, tool = build_task_summary(results)
    log(f"Aggregate: state={state} task={task!r}")

    if not update_alisya(state, task, tool):
        return 2  # script error

    # Exit code reflects health for any cron monitoring
    has_issues = any(not (r["https_ok"] and r["ssl_ok"] and r["dns_ok"]) for r in results)
    return 1 if has_issues else 0


if __name__ == "__main__":
    sys.exit(main())
