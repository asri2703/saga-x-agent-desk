"""
Saga X Agent Desk — the activity view
=====================================
Answers one question: **what happened this week?**

Built for the weekly meeting. Everything here already existed in the
database — runs, incidents, approvals, spend — but with no screen
showing it, the record lived somewhere only a psql prompt could reach.
A meeting needs the week on one page.

Deliberately a single query set behind one endpoint rather than five
calls the browser has to stitch together: the numbers must agree with
each other, which they cannot if they are fetched at different moments.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from . import config, db


def _iso(v: Any) -> Any:
    return v.isoformat() if isinstance(v, datetime) else v


def _clean(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append({k: (float(v) if hasattr(v, "quantize") else _iso(v))
                    for k, v in r.items()})
    return out


def summary(days: int = 7) -> dict:
    """Everything that happened in the window, plus the month's spend."""
    days = max(1, min(int(days), 90))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    runs = db.query("""
        select r.id, r.agent, r.trigger_kind, r.status, r.instruction,
               r.output, r.error, r.cost_usd, r.input_tokens, r.cached_tokens,
               r.output_tokens, r.queued_at, r.finished_at,
               a.title as assignment_title
          from desk.agent_runs r
          left join desk.assignments a on a.id = r.assignment_id
         where r.queued_at >= %s
         order by r.queued_at desc
         limit 200""", [since])

    spend_by_agent = db.query("""
        select agent, count(*) as runs, sum(cost_usd)::numeric(10,4) as cost_usd
          from desk.agent_runs
         where queued_at >= %s
         group by agent order by sum(cost_usd) desc nulls last""", [since])

    # What a recurring assignment actually costs. The reason assignments
    # and runs are separate tables in the first place.
    spend_by_assignment = db.query("""
        select a.title, a.agent, count(r.id) as runs,
               sum(r.cost_usd)::numeric(10,4) as cost_usd
          from desk.agent_runs r
          join desk.assignments a on a.id = r.assignment_id
         where r.queued_at >= %s
         group by a.title, a.agent order by sum(r.cost_usd) desc nulls last""",
        [since])

    incidents = db.query("""
        select i.id, i.title, i.detail, i.severity, i.status,
               i.suggested_action, i.opened_at, i.resolved_at, m.target
          from desk.incidents i
          left join desk.monitors m on m.id = i.monitor_id
         where i.opened_at >= %s or i.status in ('open','acknowledged')
         order by (i.status = 'open') desc, i.opened_at desc
         limit 50""", [since])

    approvals = db.query("""
        select id, agent, action_type, summary, risk, status, amount,
               currency, requested_at, decided_at, decided_via, error
          from desk.approvals
         where requested_at >= %s
         order by requested_at desc
         limit 50""", [since])

    month = db.query("select spent_usd, calls from desk.usage_this_month")
    spent = float(month[0]["spent_usd"]) if month else 0.0

    window_cost = sum(float(r["cost_usd"] or 0) for r in runs)
    tok_in = sum(int(r["input_tokens"] or 0) for r in runs)
    tok_cached = sum(int(r["cached_tokens"] or 0) for r in runs)

    return {
        "window_days": days,
        "since": since.isoformat(),
        "counts": {
            "runs": len(runs),
            "failed_runs": sum(1 for r in runs if r["status"] == "failed"),
            "open_incidents": sum(1 for i in incidents if i["status"] == "open"),
            "pending_approvals": sum(1 for a in approvals if a["status"] == "pending"),
        },
        "spend": {
            "window_usd": round(window_cost, 4),
            "month_usd": round(spent, 4),
            "cap_usd": config.MONTHLY_CAP_USD,
            "cap_pct": round(100 * spent / config.MONTHLY_CAP_USD, 1)
                       if config.MONTHLY_CAP_USD else 0,
            "cache_pct": round(100 * tok_cached / tok_in, 1) if tok_in else 0,
            "by_agent": _clean(spend_by_agent),
            "by_assignment": _clean(spend_by_assignment),
        },
        "runs": _clean(runs),
        "incidents": _clean(incidents),
        "approvals": _clean(approvals),
    }
