"""
Saga X Agent Desk — the scheduler
=================================
Fires assignments on a clock, and on events.

The rule Abang set: **it only ever runs work he wrote.** The scheduler
has no ability to invent an assignment, reword one, or decide something
deserves doing. It reads `desk.assignments`, finds what is due, and
hands the instruction to the agent exactly as written.

Three brakes, because a thing that runs by itself and spends money
needs more than one:

  1. `SCHEDULER_ENABLED` — a single global off switch.
  2. `assignments.enabled` — per assignment.
  3. The monthly cap in `runner.run`, which refuses regardless.

Everything consequential still goes through approvals. A scheduled run
can draft an invoice; it cannot send one.

Run from cron every 15 minutes:  python -m agents.scheduler
"""

from __future__ import annotations

import calendar
from datetime import datetime, time as dtime, timedelta, timezone

from . import config, db, runner

MAX_PER_TICK = 5  # a backlog must not empty the budget in one sweep


def _enabled() -> bool:
    return config.get("SCHEDULER_ENABLED", "1") not in ("0", "false", "no")


# ── When does this fire next ────────────────────────────────────

def next_run_at(assignment: dict, after: datetime | None = None) -> datetime | None:
    """Compute the next firing time. Returns None for assignments that
    are not schedule-driven."""
    if assignment.get("trigger_kind") != "schedule":
        return None
    # Work in Abang's timezone, return UTC. schedule_at is his local
    # wall-clock time; computing in UTC would shift every schedule by
    # eight hours and make a "morning" report arrive in the evening.
    tz = config.tzinfo()
    now = (after or datetime.now(timezone.utc)).astimezone(tz)
    kind = assignment.get("schedule_kind") or "daily"
    at: dtime = assignment.get("schedule_at") or dtime(9, 0)

    def _utc(d: datetime) -> datetime:
        return d.astimezone(timezone.utc)

    if kind == "hourly":
        return _utc((now + timedelta(hours=1)).replace(
            minute=at.minute, second=0, microsecond=0))

    base = now.replace(hour=at.hour, minute=at.minute, second=0, microsecond=0)

    if kind == "daily":
        return _utc(base if base > now else base + timedelta(days=1))

    if kind == "weekly":
        want = assignment.get("schedule_dow")
        want = 0 if want is None else int(want)
        ahead = (want - base.weekday()) % 7
        candidate = base + timedelta(days=ahead)
        return _utc(candidate if candidate > now else candidate + timedelta(days=7))

    if kind == "monthly":
        dom = int(assignment.get("schedule_dom") or 1)
        year, month = base.year, base.month
        for _ in range(2):
            day = min(dom, calendar.monthrange(year, month)[1])
            candidate = base.replace(year=year, month=month, day=day)
            if candidate > now:
                return _utc(candidate)
            month = 1 if month == 12 else month + 1
            year = year + 1 if month == 1 else year
    return None


# ── Firing ──────────────────────────────────────────────────────

def fire(assignment: dict, trigger: str = "schedule",
         detail: str | None = None) -> dict:
    """Run one assignment. The instruction is passed through untouched."""
    result = runner.run(
        assignment["agent"],
        assignment["instruction"],
        assignment_id=str(assignment["id"]),
        trigger=trigger,
        trigger_detail=detail,
        effort=assignment.get("max_effort") or "low",
    )
    full = db.select_one("assignments", filters={"id": assignment["id"]})
    db.update("assignments", {"id": assignment["id"]}, {
        "last_run_at": datetime.now(timezone.utc),
        "next_run_at": next_run_at(full or assignment),
        "run_count": (full or {}).get("run_count", 0) + 1,
    })
    return result


def tick() -> dict:
    """Cron entry point. Fires whatever is due, bounded."""
    if not _enabled():
        return {"skipped": "SCHEDULER_ENABLED is off"}

    allowed, spent, cap = db.under_cap()
    if not allowed:
        return {"skipped": f"monthly cap reached (${spent:.2f} of ${cap:.2f})"}

    due = db.select("assignments_due", limit=MAX_PER_TICK)
    fired, failed = [], []
    for a in due:
        try:
            r = fire(a)
            fired.append({"assignment": a["title"], "agent": a["agent"],
                          "status": r["status"], "cost_usd": r["cost_usd"]})
        except runner.CapReached:
            failed.append({"assignment": a["title"], "error": "cap reached mid-sweep"})
            break
        except Exception as e:
            failed.append({"assignment": a["title"], "error": str(e)[:200]})

    return {"due": len(due), "fired": fired, "failed": failed,
            "spent_usd": round(spent, 4)}


def fire_event(event_type: str, detail: str | None = None) -> dict:
    """Fire every enabled assignment waiting on this event.

    Called by the monitors when an incident opens, so an assignment like
    "tell me if a domain goes down" runs at the moment it matters rather
    than at the next tick."""
    if not _enabled():
        return {"skipped": "SCHEDULER_ENABLED is off"}
    waiting = db.select("assignments",
                        filters={"enabled": True, "trigger_kind": "event",
                                 "event_type": event_type})
    out = []
    for a in waiting[:MAX_PER_TICK]:
        try:
            r = fire(a, trigger="event", detail=detail)
            out.append({"assignment": a["title"], "status": r["status"]})
        except Exception as e:
            out.append({"assignment": a["title"], "error": str(e)[:200]})
    return {"event": event_type, "fired": out}


# ── Housekeeping the same cron can carry ────────────────────────

def housekeeping() -> dict:
    """Expire stale approvals and prune old check history. Small, and
    nothing else was going to do it."""
    from . import approvals
    expired = approvals.expire_stale()
    pruned = db.query("select desk.prune_state_history(180) as n")
    checks = db.execute(
        "delete from desk.monitor_checks where checked_at < now() - interval '90 days'")
    return {"approvals_expired": expired,
            "state_history_pruned": pruned[0]["n"] if pruned else 0,
            "monitor_checks_pruned": checks}


if __name__ == "__main__":
    print("tick        :", tick())
    print("housekeeping:", housekeeping())
