"""
Saga X Agent Desk — chat
========================
One conversation per agent, so talking to Julia about an invoice never
bleeds into what Farah thinks she was asked to do.

Only the recent tail is replayed to the model. A conversation that
grows without bound would cost more every single turn, and for this
kind of work the last few exchanges carry the context that matters —
the durable facts live in the database, not in the transcript.
"""

from __future__ import annotations

from . import config, db, runner

# Turns of history replayed to the model. Kept small on purpose: every
# replayed turn is billed again on the next message.
CONTEXT_TURNS = 12


def history(agent: str, limit: int = 50) -> list[dict]:
    """Oldest first, which is the order the UI and the model both want."""
    if agent not in config.AGENTS:
        raise ValueError(f"unknown agent: {agent}")
    rows = db.select("messages", filters={"agent": agent},
                     columns="id,role,content,created_at",
                     order="created_at desc", limit=limit)
    rows.reverse()
    return [{"role": r["role"], "content": r["content"],
             "at": r["created_at"].isoformat() if r["created_at"] else None}
            for r in rows]


def send(agent: str, message: str, effort: str | None = None) -> dict:
    """Persist the message, run the agent, persist the reply.

    The user's message is stored before the run, so a failure mid-run
    leaves a record of what was asked rather than losing it."""
    if agent not in config.AGENTS:
        raise ValueError(f"unknown agent: {agent}")
    message = (message or "").strip()
    if not message:
        raise ValueError("empty message")

    prior = history(agent, limit=CONTEXT_TURNS)
    db.insert("messages", {"agent": agent, "role": "user", "content": message})

    try:
        result = runner.run(agent, message, trigger="chat",
                            effort=effort, history=prior)
    except runner.CapReached as e:
        reply = f"⛔ {e}"
        db.insert("messages", {"agent": agent, "role": "assistant",
                               "content": reply})
        return {"ok": False, "reply": reply, "capped": True}

    reply = result.get("output") or ""
    if result.get("status") == "failed":
        reply = f"⚠️ Run failed: {result.get('error')}"
    elif result.get("status") == "needs_approval" and reply:
        reply += "\n\n⏳ Menunggu kelulusan awak."
    elif not reply:
        reply = "(no reply)"

    db.insert("messages", {"agent": agent, "role": "assistant",
                           "content": reply})

    return {"ok": result.get("status") != "failed",
            "reply": reply,
            "status": result.get("status"),
            "run_id": result.get("run_id"),
            "cost_usd": result.get("cost_usd"),
            "cached_tokens": result.get("cached_tokens"),
            "input_tokens": result.get("input_tokens")}


def clear(agent: str) -> int:
    if agent not in config.AGENTS:
        raise ValueError(f"unknown agent: {agent}")
    return len(db.delete("messages", {"agent": agent}))
