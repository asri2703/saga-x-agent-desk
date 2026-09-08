"""
Saga X Agent Desk — the tool surface
====================================
What an agent can actually do. Three tiers, matching the permission
model, and the tier is a property of the tool rather than something the
model is asked to remember:

  FREE      reads, and low-risk writes (tasks, drafts, notes)
  APPROVAL  money and outbound — the tool queues an approval and
            returns; it does not perform the action
  NONE      there is no remediation tool, on purpose

Each agent gets only its own tools. A narrow surface is the single
biggest thing that keeps an agent reliable — a model given twenty
tools will find a wrong one.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any, Callable

from . import config, db, state

FREE, APPROVAL = "free", "approval"


def _json_safe(value: Any) -> Any:
    """psycopg returns date/Decimal/UUID objects; the model needs JSON."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if hasattr(value, "__float__") and not isinstance(value, (int, float, bool)):
        return float(value)
    if not isinstance(value, (str, int, float, bool, type(None))):
        return str(value)
    return value


# ── Implementations ─────────────────────────────────────────────

def set_my_state(_agent: str, state_name: str, task: str = "") -> dict:
    if state_name not in config.VALID_STATES:
        return {"error": f"invalid state. valid: {list(config.VALID_STATES)}"}
    state.set_state(_agent, state_name, task, "agent")
    return {"ok": True, "state": state_name, "task": task}


def list_tasks(_agent: str, status: str = "", owner: str = "",
               business: str = "", limit: int = 25) -> dict:
    filters: dict[str, Any] = {}
    if status:
        filters["status"] = status
    if owner:
        filters["owner"] = owner
    if business:
        filters["business_id"] = business
    rows = db.select("tasks", filters=filters or None,
                     columns="id,title,status,priority,owner,due_on,business_id",
                     order="due_on asc", limit=limit)
    return {"count": len(rows), "tasks": _json_safe(rows)}


def create_task(_agent: str, title: str, owner: str = "", business: str = "",
                due_on: str = "", priority: str = "med",
                description: str = "") -> dict:
    if owner and owner not in config.AGENTS and owner != "abang":
        return {"error": f"unknown owner. valid: {list(config.AGENTS)} or 'abang'"}
    row = db.insert("tasks", {
        "title": title, "description": description or None,
        "owner": owner or _agent, "business_id": business or None,
        "due_on": due_on or None, "priority": priority,
        "status": "todo",
    })
    return {"ok": True, "task": _json_safe(row)}


def update_task(_agent: str, task_id: str, status: str = "",
                title: str = "", due_on: str = "", notes: str = "") -> dict:
    patch: dict[str, Any] = {}
    if status:
        patch["status"] = status
        if status == "done":
            patch["completed_at"] = datetime.now()
    if title:
        patch["title"] = title
    if due_on:
        patch["due_on"] = due_on
    if notes:
        patch["description"] = notes
    if not patch:
        return {"error": "nothing to update"}
    rows = db.update("tasks", {"id": task_id}, patch)
    if not rows:
        return {"error": "no task with that id"}
    return {"ok": True, "task": _json_safe(rows[0])}


def list_clients(_agent: str, status: str = "", business: str = "",
                 limit: int = 25) -> dict:
    filters: dict[str, Any] = {}
    if status:
        filters["status"] = status
    if business:
        filters["business_id"] = business
    rows = db.select("clients", filters=filters or None,
                     columns="id,name,company,status,business_id,whatsapp,email",
                     order="name asc", limit=limit)
    return {"count": len(rows), "clients": _json_safe(rows)}


def list_services(_agent: str, business: str = "") -> dict:
    """Prices. This table starts empty — an empty result means Abang has
    not set prices yet, not that the service is free."""
    filters: dict[str, Any] = {"active": True}
    if business:
        filters["business_id"] = business
    rows = db.select("services", filters=filters,
                     columns="id,name,kind,unit_price,currency,unit,business_id",
                     order="name asc")
    if not rows:
        return {"count": 0, "services": [],
                "note": "No prices are recorded. Ask Abang for the price; "
                        "do not estimate one."}
    return {"count": len(rows), "services": _json_safe(rows)}


def list_invoices(_agent: str, status: str = "", client_id: str = "",
                  limit: int = 25) -> dict:
    filters: dict[str, Any] = {}
    if status:
        filters["status"] = status
    if client_id:
        filters["client_id"] = client_id
    rows = db.select("invoices", filters=filters or None,
                     columns="id,number,status,client_id,issued_on,due_on,"
                             "total,amount_paid,currency,business_id",
                     order="due_on asc", limit=limit)
    return {"count": len(rows), "invoices": _json_safe(rows)}


def list_bookings(_agent: str, status: str = "", limit: int = 25) -> dict:
    filters: dict[str, Any] = {}
    if status:
        filters["status"] = status
    rows = db.select("bookings", filters=filters or None,
                     columns="id,space_name,client_id,starts_at,ends_at,"
                             "headcount,status,quoted_total",
                     order="starts_at asc", limit=limit)
    return {"count": len(rows), "bookings": _json_safe(rows)}


def list_content(_agent: str, status: str = "", limit: int = 25) -> dict:
    filters: dict[str, Any] = {}
    if status:
        filters["status"] = status
    rows = db.select("content", filters=filters or None,
                     columns="id,title,channel,status,publish_at,business_id",
                     order="publish_at asc", limit=limit)
    return {"count": len(rows), "content": _json_safe(rows)}


def draft_content(_agent: str, title: str, body: str, channel: str = "",
                  business: str = "", client_id: str = "",
                  publish_at: str = "") -> dict:
    """Draft only. Publishing to Buffer is not connected."""
    row = db.insert("content", {
        "title": title, "body": body, "channel": channel or None,
        "business_id": business or None, "client_id": client_id or None,
        "publish_at": publish_at or None, "status": "drafting",
    })
    return {"ok": True, "content": _json_safe(row),
            "note": "Saved as a draft. Publishing is not connected."}


def list_incidents(_agent: str, status: str = "open", limit: int = 20) -> dict:
    rows = db.select("incidents", filters={"status": status} if status else None,
                     columns="id,title,detail,severity,status,suggested_action,opened_at",
                     order="opened_at desc", limit=limit)
    return {"count": len(rows), "incidents": _json_safe(rows)}


def monitor_status(_agent: str) -> dict:
    monitors = db.select("monitors", filters={"enabled": True},
                         columns="id,name,target,kind")
    out = []
    for m in monitors:
        last = db.select("monitor_checks", filters={"monitor_id": m["id"]},
                         columns="ok,http_status,response_ms,ssl_days_left,error,checked_at",
                         order="checked_at desc", limit=1)
        out.append({"name": m["name"], "target": m["target"],
                    "last_check": _json_safe(last[0]) if last else None})
    return {"count": len(out), "monitors": out}


def business_summary(_agent: str) -> dict:
    """One call instead of six, so a run does not burn budget on
    orientation before it gets to the actual question."""
    return _json_safe({
        "open_tasks": db.count("tasks", {"status": ("in", ["todo", "in_progress", "blocked"])}),
        "overdue_tasks": db.count("tasks", {"status": ("in", ["todo", "in_progress"]),
                                            "due_on": ("<", date.today())}),
        "clients": db.count("clients"),
        "unpaid_invoices": db.count("invoices", {"status": ("in", ["sent", "partial", "overdue"])}),
        "open_incidents": db.count("incidents", {"status": "open"}),
        "pending_approvals": db.count("approvals", {"status": "pending"}),
        "services_priced": db.count("services"),
        "upcoming_bookings": db.count("bookings", {"status": ("in", ["pending", "confirmed"])}),
    })


def create_assignment(_agent: str, title: str, instruction: str,
                      schedule_kind: str = "", schedule_at: str = "",
                      schedule_dow: int | None = None,
                      schedule_dom: int | None = None,
                      event_type: str = "", business: str = "",
                      max_effort: str = "low") -> dict:
    """Standing instruction that fires on a clock or on an event.

    The instruction is stored exactly as Abang worded it; the scheduler
    replays it verbatim and cannot reword or invent work."""
    if schedule_kind and event_type:
        return {"error": "an assignment is either scheduled or event-driven, not both"}
    trigger = "schedule" if schedule_kind else ("event" if event_type else "manual")
    if trigger == "schedule" and schedule_kind not in ("hourly", "daily", "weekly", "monthly"):
        return {"error": "schedule_kind must be hourly, daily, weekly or monthly"}

    row = db.insert("assignments", {
        "agent": _agent, "title": title, "instruction": instruction,
        "business_id": business or None, "trigger_kind": trigger,
        "schedule_kind": schedule_kind or None,
        "schedule_at": schedule_at or None,
        "schedule_dow": schedule_dow, "schedule_dom": schedule_dom,
        "event_type": event_type or None,
        "max_effort": max_effort if max_effort in
            ("minimal", "low", "medium", "high", "max") else "low",
        "enabled": True,
    })
    if trigger == "schedule":
        from . import scheduler
        nxt = scheduler.next_run_at(row)
        db.update("assignments", {"id": row["id"]}, {"next_run_at": nxt})
        row["next_run_at"] = nxt
    return {"ok": True, "assignment": _json_safe(row),
            "note": "Saved. It runs only while enabled, and money still needs approval."}


def list_assignments(_agent: str, mine_only: bool = True) -> dict:
    filters = {"agent": _agent} if mine_only else None
    rows = db.select("assignments", filters=filters,
                     columns="id,agent,title,instruction,trigger_kind,schedule_kind,"
                             "schedule_at,event_type,enabled,last_run_at,next_run_at,run_count",
                     order="created_at desc", limit=30)
    return {"count": len(rows), "assignments": _json_safe(rows)}


def set_assignment_enabled(_agent: str, assignment_id: str,
                           enabled: bool = True) -> dict:
    rows = db.update("assignments", {"id": assignment_id}, {"enabled": enabled})
    if not rows:
        return {"error": "no assignment with that id"}
    return {"ok": True, "title": rows[0]["title"], "enabled": enabled}


def mastery_status(_agent: str) -> dict:
    """Mastery Signal automation health: crons, live signals, state files.

    Read-only by design. That bot is live revenue; this desk watches it
    and does not touch it."""
    from . import mastery
    return _json_safe(mastery.summary())


# ── Sites ───────────────────────────────────────────────────────
# Drafting is free; publishing to the public internet is not. Same
# shape as content: write freely, ship only with approval.

ALLOWED_SITE_EXT = (".html", ".css", ".js", ".json", ".txt", ".svg", ".xml", ".webmanifest")
MAX_SITE_BYTES = 2_000_000


def build_site(_agent: str, name: str, domain: str, pages: list | str,
               brief: str = "", business: str = "") -> dict:
    """Create or replace a site draft. Nothing is published by this.

    `pages` is [{"path": "index.html", "content": "<!doctype html>..."}].
    Paths are restricted to static web files and cannot escape the site
    directory — a payload is replayed verbatim on approval, so a path
    like ../../etc would be written exactly as given."""
    if isinstance(pages, str):
        try:
            pages = json.loads(pages)
        except json.JSONDecodeError:
            return {"error": "pages must be a list of {path, content}"}
    if not isinstance(pages, list) or not pages:
        return {"error": "pages must be a non-empty list of {path, content}"}

    domain = domain.strip().lower().replace("https://", "").replace("http://", "").strip("/")
    if not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", domain):
        return {"error": f"not a valid domain: {domain}"}

    clean, total = [], 0
    for pg in pages:
        path = str(pg.get("path", "")).strip().lstrip("/")
        body = pg.get("content") or ""
        if not path or ".." in path or path.startswith(("/", "\\")) or ":" in path:
            return {"error": f"unsafe path: {path!r}"}
        if not path.lower().endswith(ALLOWED_SITE_EXT):
            return {"error": f"file type not allowed: {path!r}. "
                             f"allowed: {', '.join(ALLOWED_SITE_EXT)}"}
        total += len(body)
        clean.append({"path": path, "content": body})
    if total > MAX_SITE_BYTES:
        return {"error": f"site is {total} bytes; limit is {MAX_SITE_BYTES}"}
    if not any(p["path"] == "index.html" for p in clean):
        return {"error": "a site needs an index.html"}

    existing = db.select_one("sites", filters={"domain": domain})
    if existing:
        site = db.update("sites", {"id": existing["id"]}, {
            "name": name, "brief": brief or existing.get("brief"),
            "status": "draft", "updated_at": datetime.now()})[0]
        db.delete("site_files", {"site_id": site["id"]})
    else:
        site = db.insert("sites", {
            "name": name, "domain": domain, "brief": brief or None,
            "business_id": business or None, "created_by": _agent,
            "status": "draft"})

    for pg in clean:
        db.insert("site_files", {"site_id": site["id"], **pg})

    return {"ok": True, "site_id": str(site["id"]), "domain": domain,
            "files": [p["path"] for p in clean], "bytes": total,
            "note": "Saved as a draft. Nothing is public until Abang "
                    "approves a publish."}


def list_sites(_agent: str) -> dict:
    return {"sites": _json_safe(db.select("sites_overview"))}


def get_site_file(_agent: str, domain: str, path: str = "index.html") -> dict:
    site = db.select_one("sites", filters={"domain": domain.lower()})
    if not site:
        return {"error": f"no site for {domain}"}
    f = db.select_one("site_files", filters={"site_id": site["id"], "path": path})
    if not f:
        return {"error": f"no file {path} in {domain}"}
    return {"path": path, "content": f["content"]}


def publish_site(_agent: str, domain: str, run_id: str | None = None) -> dict:
    """Queue a site for publication. Does not publish."""
    domain = domain.strip().lower()
    site = db.select_one("sites", filters={"domain": domain})
    if not site:
        return {"error": f"no site for {domain}. Build it first."}
    files = db.select("site_files", filters={"site_id": site["id"]}, columns="path")
    if not files:
        return {"error": "site has no files"}
    db.update("sites", {"id": site["id"]}, {"status": "pending"})
    return request_approval(
        _agent, "publish_site",
        f"Terbitkan {site['name']} ke {domain} ({len(files)} fail)",
        {"site_id": str(site["id"]), "domain": domain},
        risk="outbound",
        context=f"Files: {', '.join(f['path'] for f in files)}",
        run_id=run_id)


# ── Alisya's own workspace ──────────────────────────────────────
# Managing what she watches is her job, not remediation. The line is
# the machines: she may change her watchlist and her incident records,
# she may not touch DNS, nginx, or a server.

def add_monitor(_agent: str, name: str, target: str, kind: str = "https",
                business: str = "", interval_mins: int = 360,
                fail_threshold: int = 2) -> dict:
    existing = db.select("monitors", filters={"kind": kind, "target": target}, limit=1)
    if existing:
        return {"error": f"already monitored: {target}",
                "monitor_id": str(existing[0]["id"])}
    row = db.insert("monitors", {
        "name": name, "target": target, "kind": kind,
        "business_id": business or None, "owner_agent": _agent,
        "interval_mins": interval_mins, "fail_threshold": fail_threshold,
    })
    return {"ok": True, "monitor": _json_safe(row)}


def set_monitor_enabled(_agent: str, target: str, enabled: bool = True) -> dict:
    rows = db.update("monitors", {"target": target}, {"enabled": enabled})
    if not rows:
        return {"error": f"no monitor for {target}"}
    # A monitor turned off should not leave its incident hanging open.
    if not enabled:
        for inc in db.select("incidents",
                             filters={"monitor_id": rows[0]["id"],
                                      "status": ("in", ["open", "acknowledged"])}):
            db.update("incidents", {"id": inc["id"]}, {
                "status": "resolved", "resolved_at": datetime.now(),
            })
    return {"ok": True, "target": target, "enabled": enabled,
            "note": "Monitoring stopped; open incidents closed."
                    if not enabled else "Monitoring resumed."}


def resolve_incident(_agent: str, incident_id: str, note: str = "") -> dict:
    """Close an incident. Bookkeeping — it records that the matter is
    settled, it does not fix anything."""
    rows = db.update("incidents", {"id": incident_id}, {
        "status": "resolved", "resolved_at": datetime.now(),
        "suggested_action": note or None,
    })
    if not rows:
        return {"error": "no incident with that id"}
    return {"ok": True, "title": rows[0]["title"], "status": "resolved"}


def acknowledge_incident(_agent: str, incident_id: str) -> dict:
    rows = db.update("incidents", {"id": incident_id}, {
        "status": "acknowledged", "acknowledged_at": datetime.now()})
    if not rows:
        return {"error": "no incident with that id"}
    return {"ok": True, "title": rows[0]["title"], "status": "acknowledged"}


# ── Records ─────────────────────────────────────────────────────

def create_client(_agent: str, name: str, business: str = "", company: str = "",
                  email: str = "", phone: str = "", whatsapp: str = "",
                  status: str = "lead", source: str = "", notes: str = "") -> dict:
    dupes = db.select("clients", filters={"name": name}, limit=1)
    if dupes:
        return {"error": f"a client named '{name}' already exists",
                "client_id": str(dupes[0]["id"])}
    row = db.insert("clients", {
        "name": name, "business_id": business or None, "company": company or None,
        "email": email or None, "phone": phone or None,
        "whatsapp": whatsapp or None, "status": status,
        "source": source or None, "notes": notes or None,
    })
    return {"ok": True, "client": _json_safe(row)}


def update_client(_agent: str, client_id: str, **fields) -> dict:
    allowed = {"name", "company", "email", "phone", "whatsapp",
               "status", "source", "notes", "business_id"}
    patch = {k: v for k, v in fields.items() if k in allowed and v not in ("", None)}
    if not patch:
        return {"error": f"nothing to update. fields: {sorted(allowed)}"}
    patch["updated_at"] = datetime.now()
    rows = db.update("clients", {"id": client_id}, patch)
    if not rows:
        return {"error": "no client with that id"}
    return {"ok": True, "client": _json_safe(rows[0])}


def update_content(_agent: str, content_id: str, status: str = "",
                   title: str = "", body: str = "", publish_at: str = "") -> dict:
    patch: dict[str, Any] = {}
    if status:
        patch["status"] = status
        if status == "published":
            return {"error": "publishing is not connected — Buffer is on hold. "
                             "Use 'scheduled' and tell Abang."}
    for k, v in (("title", title), ("body", body), ("publish_at", publish_at)):
        if v:
            patch[k] = v
    if not patch:
        return {"error": "nothing to update"}
    patch["updated_at"] = datetime.now()
    rows = db.update("content", {"id": content_id}, patch)
    if not rows:
        return {"error": "no content with that id"}
    return {"ok": True, "content": _json_safe(rows[0])}


def create_booking(_agent: str, space_name: str, starts_at: str, ends_at: str,
                   client_id: str = "", headcount: int | None = None,
                   quoted_total: float | None = None, notes: str = "") -> dict:
    """A booking records what was agreed. The invoice that follows is
    where the money gate sits."""
    row = db.insert("bookings", {
        "space_name": space_name, "starts_at": starts_at, "ends_at": ends_at,
        "client_id": client_id or None, "headcount": headcount,
        "quoted_total": quoted_total, "notes": notes or None,
        "status": "pending",
    })
    return {"ok": True, "booking": _json_safe(row)}


def create_subscription(_agent: str, client_id: str = "", telegram_user: str = "",
                        amount: float | None = None, renews_on: str = "",
                        service_id: str = "", notes: str = "") -> dict:
    row = db.insert("subscriptions", {
        "client_id": client_id or None, "telegram_user": telegram_user or None,
        "service_id": service_id or None, "amount": amount,
        "renews_on": renews_on or None, "notes": notes or None,
        "status": "active",
    })
    return {"ok": True, "subscription": _json_safe(row)}


# ── Money: these queue, they do not act ─────────────────────────
# Each builds its own well-formed payload rather than asking the model
# to construct a generic one — a malformed payload fails at execution,
# after Abang has already approved it.

def set_service_price(_agent: str, name: str, unit_price: float,
                      business: str = "agency", kind: str = "service",
                      unit: str = "per_project", billing_period: str = "",
                      description: str = "", run_id: str | None = None) -> dict:
    return request_approval(
        _agent, "create_service",
        f"Set harga: {name} — {business} — MYR {unit_price:,.2f} {unit}",
        {"name": name, "unit_price": unit_price, "business_id": business,
         "kind": kind, "unit": unit,
         "billing_period": billing_period or None,
         "description": description or None},
        risk="money", amount=unit_price, run_id=run_id)


def record_expense(_agent: str, description: str, amount: float,
                   business: str = "", category: str = "",
                   spent_on: str = "", run_id: str | None = None) -> dict:
    return request_approval(
        _agent, "record_expense",
        f"Rekod perbelanjaan: {description} — MYR {amount:,.2f}",
        {"description": description, "amount": amount,
         "business_id": business or None, "category": category or None,
         "spent_on": spent_on or None},
        risk="money", amount=amount, run_id=run_id)


def update_invoice_status(_agent: str, invoice_id: str, status: str = "",
                          amount_paid: float | None = None,
                          run_id: str | None = None) -> dict:
    inv = db.select_one("invoices", filters={"id": invoice_id})
    if not inv:
        return {"error": "no invoice with that id"}
    if amount_paid is not None:
        return request_approval(
            _agent, "record_payment",
            f"Rekod bayaran {inv['currency']} {amount_paid:,.2f} "
            f"untuk invois {inv['number']}",
            {"invoice_id": invoice_id, "amount": amount_paid},
            risk="money", amount=amount_paid, run_id=run_id)
    return request_approval(
        _agent, "set_invoice_status",
        f"Tukar status invois {inv['number']} kepada {status}",
        {"invoice_id": invoice_id, "status": status},
        risk="money", run_id=run_id)


def request_approval(_agent: str, action_type: str, summary: str,
                     payload: dict | str, risk: str = "money",
                     amount: float | None = None, context: str = "",
                     run_id: str | None = None) -> dict:
    """Queue an action for Abang. Does NOT perform it.

    The payload is stored verbatim and replayed on approval, so what he
    approves is exactly what happens."""
    if risk not in ("money", "outbound", "destructive", "other"):
        risk = "other"
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {"raw": payload}

    dupes = db.select("approvals",
                      filters={"status": "pending", "agent": _agent,
                               "summary": summary}, limit=1)
    if dupes:
        return {"ok": False, "note": "An identical approval is already pending.",
                "approval_id": str(dupes[0]["id"])}

    row = db.insert("approvals", {
        "agent": _agent, "action_type": action_type, "summary": summary[:500],
        "payload": json.dumps(payload), "risk": risk,
        "amount": amount, "context": context or None, "run_id": run_id,
    })
    return {"ok": True, "approval_id": str(row["id"]), "status": "pending",
            "note": "Queued for Abang. Nothing has happened yet."}


# ── Registry ────────────────────────────────────────────────────
# name -> (callable, tier, JSON schema)

def _t(name: str, desc: str, props: dict, required: list[str] | None = None) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props,
                       "required": required or [],
                       "additionalProperties": False}}}


S = {"type": "string"}
I = {"type": "integer"}
N = {"type": "number"}

REGISTRY: dict[str, tuple[Callable, str, dict]] = {
    "set_my_state": (set_my_state, FREE, _t(
        "set_my_state",
        "Set your own state on the desk. Do this when you start real work and "
        "again when you finish. A stale state misleads Abang.",
        {"state_name": {**S, "enum": list(config.VALID_STATES)},
         "task": {**S, "description": "Short, specific line shown on the dashboard."}},
        ["state_name"])),

    "business_summary": (business_summary, FREE, _t(
        "business_summary",
        "Counts across everything: open and overdue tasks, unpaid invoices, "
        "open incidents, pending approvals, priced services. Use this first "
        "to orient rather than making several list calls.",
        {})),

    "list_tasks": (list_tasks, FREE, _t(
        "list_tasks", "List tasks, optionally filtered.",
        {"status": {**S, "enum": ["todo", "in_progress", "blocked", "done", "cancelled"]},
         "owner": S, "business": {**S, "enum": ["agency", "space", "signals"]},
         "limit": I})),

    "create_task": (create_task, FREE, _t(
        "create_task", "Create a task. Low risk, no approval needed.",
        {"title": S, "owner": {**S, "description": "agent id, or 'abang'"},
         "business": {**S, "enum": ["agency", "space", "signals"]},
         "due_on": {**S, "description": "YYYY-MM-DD"},
         "priority": {**S, "enum": ["low", "med", "high", "urgent"]},
         "description": S}, ["title"])),

    "update_task": (update_task, FREE, _t(
        "update_task", "Update or close a task.",
        {"task_id": S,
         "status": {**S, "enum": ["todo", "in_progress", "blocked", "done", "cancelled"]},
         "title": S, "due_on": S, "notes": S}, ["task_id"])),

    "list_clients": (list_clients, FREE, _t(
        "list_clients", "List clients.",
        {"status": {**S, "enum": ["lead", "active", "dormant", "lost"]},
         "business": {**S, "enum": ["agency", "space", "signals"]}, "limit": I})),

    "list_services": (list_services, FREE, _t(
        "list_services",
        "List priced services. If this returns nothing, no prices are recorded — "
        "ask Abang rather than estimating.",
        {"business": {**S, "enum": ["agency", "space", "signals"]}})),

    "list_invoices": (list_invoices, FREE, _t(
        "list_invoices", "List invoices.",
        {"status": {**S, "enum": ["draft", "sent", "partial", "paid", "overdue", "void"]},
         "client_id": S, "limit": I})),

    "list_bookings": (list_bookings, FREE, _t(
        "list_bookings", "List hall/space bookings by start time.",
        {"status": {**S, "enum": ["enquiry", "pending", "confirmed", "completed",
                                  "cancelled", "no_show"]}, "limit": I})),

    "list_content": (list_content, FREE, _t(
        "list_content", "List marketing content items.",
        {"status": {**S, "enum": ["idea", "drafting", "review", "scheduled",
                                  "published", "archived"]}, "limit": I})),

    "draft_content": (draft_content, FREE, _t(
        "draft_content",
        "Save a content draft. Does not publish — Buffer is not connected.",
        {"title": S, "body": S,
         "channel": {**S, "enum": ["facebook", "instagram", "tiktok", "telegram",
                                   "linkedin", "x", "email", "blog", "other"]},
         "business": {**S, "enum": ["agency", "space", "signals"]},
         "client_id": S, "publish_at": S}, ["title", "body"])),

    "list_incidents": (list_incidents, FREE, _t(
        "list_incidents", "List infrastructure incidents.",
        {"status": {**S, "enum": ["open", "acknowledged", "resolved"]}, "limit": I})),

    "monitor_status": (monitor_status, FREE, _t(
        "monitor_status", "Latest check result for every monitored property.", {})),

    "create_assignment": (create_assignment, FREE, _t(
        "create_assignment",
        "Save a standing instruction from Abang so it runs on a schedule "
        "('setiap hari', 'setiap Isnin') or when something happens. Store his "
        "wording as he gave it — it is replayed verbatim. Use this when he asks "
        "for something recurring rather than doing it once and forgetting.",
        {"title": {**S, "description": "Short label, e.g. 'Semakan overdue harian'"},
         "instruction": {**S, "description": "Abang's instruction, in his words."},
         "schedule_kind": {**S, "enum": ["hourly", "daily", "weekly", "monthly"]},
         "schedule_at": {**S, "description": "Time of day, HH:MM"},
         "schedule_dow": {**I, "description": "Weekly: 0=Mon .. 6=Sun"},
         "schedule_dom": {**I, "description": "Monthly: day 1-28"},
         "event_type": {**S, "enum": ["monitor_down", "monitor_recovered",
                                      "ssl_expiring", "invoice_overdue",
                                      "booking_upcoming", "subscription_renewing"]},
         "business": {**S, "enum": ["agency", "space", "signals"]},
         "max_effort": {**S, "enum": ["minimal", "low", "medium", "high", "max"]}},
        ["title", "instruction"])),

    "list_assignments": (list_assignments, FREE, _t(
        "list_assignments", "Your standing instructions and when each next runs.",
        {"mine_only": {"type": "boolean"}})),

    "set_assignment_enabled": (set_assignment_enabled, FREE, _t(
        "set_assignment_enabled", "Turn a standing instruction on or off.",
        {"assignment_id": S, "enabled": {"type": "boolean"}}, ["assignment_id"])),

    "mastery_status": (mastery_status, FREE, _t(
        "mastery_status",
        "Health of the Mastery Signal automation — cron jobs, live signal count, "
        "state files. Read-only. If it reports unreachable, say so plainly: the "
        "check did not happen, which is not the same as everything being fine.",
        {})),

    "build_site": (build_site, FREE, _t(
        "build_site",
        "Create or replace a website draft: complete files, ready to publish. "
        "Static only — HTML, CSS, JS, images as SVG. Nothing becomes public "
        "until Abang approves a publish, so write the real thing rather than a "
        "sketch. Replaces every file for that domain, so send the whole site.",
        {"name": S, "domain": {**S, "description": "e.g. space2.sagaxventures.com"},
         "pages": {"type": "array", "description": "[{path, content}], must include index.html",
                   "items": {"type": "object",
                             "properties": {"path": S, "content": S},
                             "required": ["path", "content"]}},
         "brief": {**S, "description": "What Abang asked for, in his words."},
         "business": {**S, "enum": ["agency", "space", "signals"]}},
        ["name", "domain", "pages"])),

    "list_sites": (list_sites, FREE, _t(
        "list_sites", "Sites you have built, their status and file counts.", {})),

    "get_site_file": (get_site_file, FREE, _t(
        "get_site_file", "Read one file back from a site draft.",
        {"domain": S, "path": S}, ["domain"])),

    "publish_site": (publish_site, APPROVAL, _t(
        "publish_site",
        "Queue a site to go live. Does not publish — Abang approves, and a "
        "fixed pipeline copies the files. You never touch the web server.",
        {"domain": S}, ["domain"])),

    "add_monitor": (add_monitor, FREE, _t(
        "add_monitor", "Start watching a domain or endpoint.",
        {"name": S, "target": {**S, "description": "domain, no scheme"},
         "kind": {**S, "enum": ["https", "dns", "ssl", "cron", "telegram_bot", "custom"]},
         "business": {**S, "enum": ["agency", "space", "signals"]},
         "interval_mins": I, "fail_threshold": I}, ["name", "target"])),

    "set_monitor_enabled": (set_monitor_enabled, FREE, _t(
        "set_monitor_enabled",
        "Turn monitoring of a target on or off. Turning it off also closes any "
        "incident still open for it. Use when Abang says a domain is retired — "
        "a monitor left failing forever teaches him to ignore your alerts.",
        {"target": S, "enabled": {"type": "boolean"}}, ["target"])),

    "acknowledge_incident": (acknowledge_incident, FREE, _t(
        "acknowledge_incident", "Mark an incident as seen and being handled.",
        {"incident_id": S}, ["incident_id"])),

    "resolve_incident": (resolve_incident, FREE, _t(
        "resolve_incident",
        "Close an incident. Records that the matter is settled; it does not fix "
        "anything and does not imply you did.",
        {"incident_id": S, "note": S}, ["incident_id"])),

    "create_client": (create_client, FREE, _t(
        "create_client", "Add a client. A record, not money — no approval needed.",
        {"name": S, "business": {**S, "enum": ["agency", "space", "signals"]},
         "company": S, "email": S, "phone": S, "whatsapp": S,
         "status": {**S, "enum": ["lead", "active", "dormant", "lost"]},
         "source": S, "notes": S}, ["name"])),

    "update_client": (update_client, FREE, _t(
        "update_client", "Change a client's details.",
        {"client_id": S, "name": S, "company": S, "email": S, "phone": S,
         "whatsapp": S, "status": S, "source": S, "notes": S}, ["client_id"])),

    "update_content": (update_content, FREE, _t(
        "update_content",
        "Move a content item along, or edit it. You cannot set 'published' — "
        "Buffer is not connected and claiming otherwise would be a lie.",
        {"content_id": S,
         "status": {**S, "enum": ["idea", "drafting", "review", "scheduled", "archived"]},
         "title": S, "body": S, "publish_at": S}, ["content_id"])),

    "create_booking": (create_booking, FREE, _t(
        "create_booking",
        "Record a hall or space booking — a slot in time, not a project.",
        {"space_name": S, "starts_at": {**S, "description": "ISO datetime"},
         "ends_at": S, "client_id": S, "headcount": I, "quoted_total": N,
         "notes": S}, ["space_name", "starts_at", "ends_at"])),

    "create_subscription": (create_subscription, FREE, _t(
        "create_subscription", "Record a recurring signal subscription.",
        {"client_id": S, "telegram_user": S, "amount": N,
         "renews_on": {**S, "description": "YYYY-MM-DD"},
         "service_id": S, "notes": S})),

    "set_service_price": (set_service_price, APPROVAL, _t(
        "set_service_price",
        "Record a price Abang has given you. Queues for his approval; the price "
        "is not live until he confirms. Never invent the number.",
        {"name": S, "unit_price": N,
         "business": {**S, "enum": ["agency", "space", "signals"]},
         "kind": {**S, "enum": ["service", "product", "subscription"]},
         "unit": {**S, "enum": ["per_project", "per_month", "per_hour", "per_day",
                                "per_booking", "per_item", "per_campaign"]},
         "billing_period": {**S, "enum": ["monthly", "quarterly", "yearly"]},
         "description": S}, ["name", "unit_price"])),

    "record_expense": (record_expense, APPROVAL, _t(
        "record_expense", "Queue an expense for approval.",
        {"description": S, "amount": N,
         "business": {**S, "enum": ["agency", "space", "signals"]},
         "category": S, "spent_on": S}, ["description", "amount"])),

    "update_invoice_status": (update_invoice_status, APPROVAL, _t(
        "update_invoice_status",
        "Queue a payment record or an invoice status change for approval.",
        {"invoice_id": S, "status": {**S, "enum": ["draft", "sent", "partial",
                                                   "paid", "overdue", "void"]},
         "amount_paid": N}, ["invoice_id"])),

    "request_approval": (request_approval, APPROVAL, _t(
        "request_approval",
        "Queue an action needing Abang's approval — invoices, prices, payments, "
        "or anything sent to a real client. This does NOT perform the action. "
        "Write the summary for someone glancing at a phone: what, who, how much.",
        {"action_type": {**S, "description": "e.g. create_invoice, update_price, send_message"},
         "summary": {**S, "description": "One line, plain language."},
         "payload": {"type": "object", "description": "Exact action, replayed on approval."},
         "risk": {**S, "enum": ["money", "outbound", "destructive", "other"]},
         "amount": N, "context": S},
        ["action_type", "summary", "payload", "risk"])),
}


# Deliberately no remediation tool for anyone, Alisya included.
AGENT_TOOLS: dict[str, list[str]] = {
    "putri": ["set_my_state", "business_summary", "list_tasks", "create_task",
              "list_clients", "list_invoices", "list_bookings", "list_content",
              "list_incidents", "monitor_status", "mastery_status",
              "create_assignment", "list_assignments", "set_assignment_enabled"],
    "alisya": ["set_my_state", "monitor_status", "list_incidents",
               "list_tasks", "create_task", "create_assignment", "list_assignments", "set_assignment_enabled",
               "add_monitor", "set_monitor_enabled", "acknowledge_incident", "resolve_incident", "mastery_status"],
    "julia": ["set_my_state", "business_summary", "list_clients", "list_services",
              "list_invoices", "list_bookings", "list_tasks", "create_task",
              "request_approval", "create_assignment", "list_assignments",
              "set_assignment_enabled", "create_client", "update_client",
              "set_service_price", "record_expense", "update_invoice_status",
              "create_booking", "create_subscription"],
    "farah": ["set_my_state", "list_content", "draft_content", "list_clients",
              "list_tasks", "create_task", "request_approval", "create_assignment",
              "list_assignments", "set_assignment_enabled", "update_content",
              "create_client", "update_client", "build_site", "list_sites", "get_site_file", "publish_site"],
    "delisha": ["set_my_state", "business_summary", "list_tasks", "create_task",
                "update_task", "list_clients", "list_invoices", "list_content",
                "create_assignment", "list_assignments", "set_assignment_enabled",
                "create_client", "update_client"],
}


def tools_for(agent: str) -> list[dict]:
    """Schemas in a fixed order — a varying tool list would invalidate the
    cached prefix on every call."""
    return [REGISTRY[n][2] for n in AGENT_TOOLS.get(agent, []) if n in REGISTRY]


def execute(agent: str, name: str, args: dict, run_id: str | None = None) -> dict:
    if name not in AGENT_TOOLS.get(agent, []):
        return {"error": f"{agent} does not have the tool '{name}'"}
    fn, tier, _schema = REGISTRY[name]
    try:
        if tier == APPROVAL:
            return fn(agent, run_id=run_id, **args)
        return fn(agent, **args)
    except TypeError as e:
        return {"error": f"bad arguments for {name}: {e}"}
    except Exception as e:
        return {"error": f"{name} failed: {str(e)[:200]}"}
