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
              "list_incidents", "monitor_status",
              "create_assignment", "list_assignments", "set_assignment_enabled"],
    "alisya": ["set_my_state", "monitor_status", "list_incidents",
               "list_tasks", "create_task", "create_assignment", "list_assignments", "set_assignment_enabled"],
    "julia": ["set_my_state", "business_summary", "list_clients", "list_services",
              "list_invoices", "list_bookings", "list_tasks", "create_task",
              "request_approval", "create_assignment", "list_assignments", "set_assignment_enabled"],
    "farah": ["set_my_state", "list_content", "draft_content", "list_clients",
              "list_tasks", "create_task", "request_approval", "create_assignment", "list_assignments", "set_assignment_enabled"],
    "delisha": ["set_my_state", "business_summary", "list_tasks", "create_task",
                "update_task", "list_clients", "list_invoices", "list_content",
                "create_assignment", "list_assignments", "set_assignment_enabled"],
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
