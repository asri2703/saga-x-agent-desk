"""
Saga X Agent Desk — the runner
==============================
Takes an instruction, gives it to an agent, lets the agent use its
tools, records what it cost.

Three things this refuses to do:

  * Call the model when the month's spend is at the cap. A budget that
    is not enforced is not a budget.
  * Loop forever. MAX_TURNS bounds a run; an agent that has not
    finished by then reports what it has rather than spending more.
  * Silently swallow a failure. A failed run is recorded as failed,
    with the error, and still carries its cost.

Cost is recorded per run, not just per month, so "which assignment is
expensive" is answerable.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI

from . import config, db, prompts, tools

MAX_TURNS = 8
MAX_OUTPUT_TOKENS = 4000

# USD per 1,000,000 tokens. Sept 2026.
# `cached` is the rate for prefix cache hits; treated as 10% of input,
# which is the usual discount — verify against the first real invoice
# and correct here rather than letting the ledger drift from the bill.
PRICING = {
    "gpt-5.6-sol":   {"input": 4.00, "cached": 0.40, "output": 20.00},
    "gpt-5.6-terra": {"input": 2.00, "cached": 0.20, "output": 12.00},
    "gpt-5.6-luna":  {"input": 0.20, "cached": 0.02, "output": 1.20},
}


class CapReached(RuntimeError):
    pass


def _client() -> OpenAI:
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    kwargs: dict[str, Any] = {"api_key": config.OPENAI_API_KEY}
    if config.OPENAI_ORG_ID:
        kwargs["organization"] = config.OPENAI_ORG_ID
    return OpenAI(**kwargs)


def _cost(model: str, inp: int, cached: int, out: int) -> float:
    p = PRICING.get(model) or PRICING["gpt-5.6-sol"]
    # `inp` from the API includes cached tokens; bill the uncached part
    # at full rate and the cached part at the cache rate.
    uncached = max(inp - cached, 0)
    return round(
        uncached / 1e6 * p["input"]
        + cached / 1e6 * p["cached"]
        + out / 1e6 * p["output"], 6)


def _usage_of(resp: Any) -> tuple[int, int, int]:
    u = getattr(resp, "usage", None)
    if not u:
        return 0, 0, 0
    inp = getattr(u, "input_tokens", 0) or 0
    out = getattr(u, "output_tokens", 0) or 0
    cached = 0
    details = getattr(u, "input_tokens_details", None)
    if details is not None:
        cached = getattr(details, "cached_tokens", 0) or 0
    return inp, cached, out


def run(agent: str, instruction: str, *, assignment_id: str | None = None,
        trigger: str = "manual", effort: str | None = None,
        trigger_detail: str | None = None,
        history: list[dict] | None = None) -> dict:
    """Execute one run. Returns the run row plus the agent's final text.

    `history` carries prior chat turns as [{"role","content"}, ...]. It
    is placed after the cached prefix (instructions + tools) so adding a
    turn does not invalidate the cache."""
    if agent not in config.AGENTS:
        raise ValueError(f"unknown agent: {agent}")

    allowed, spent, cap = db.under_cap()
    if not allowed:
        raise CapReached(
            f"Monthly cap reached: ${spent:.2f} of ${cap:.2f}. "
            f"Raise MONTHLY_CAP_USD or wait for the new month.")

    model = config.OPENAI_MODEL
    effort = effort or config.OPENAI_REASONING_EFFORT

    run_row = db.insert("agent_runs", {
        "assignment_id": assignment_id, "agent": agent,
        "trigger_kind": trigger, "trigger_detail": trigger_detail,
        "instruction": instruction, "status": "running",
        "model": model, "effort": effort,
        "started_at": datetime.now(timezone.utc),
    })
    run_id = str(run_row["id"])

    client = _client()
    schemas = tools.tools_for(agent)
    # Responses API wants tools flattened, not nested under "function".
    flat_tools = [{"type": "function", **t["function"]} for t in schemas]

    conversation: list[dict] = [
        {"role": m["role"], "content": m["content"]}
        for m in (history or [])
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    conversation.append({"role": "user", "content": instruction})
    tot_in = tot_cached = tot_out = 0
    final_text = ""
    error: str | None = None
    needs_approval = False

    try:
        for _turn in range(MAX_TURNS):
            resp = client.responses.create(
                model=model,
                instructions=prompts.system_prompt(agent),
                input=conversation,
                tools=flat_tools,
                reasoning={"effort": effort},
                max_output_tokens=MAX_OUTPUT_TOKENS,
                # Groups cache lookups per agent, so Julia's prefix is not
                # evicted by Farah's.
                prompt_cache_key=f"sagax-desk-{agent}",
                store=False,
            )
            i, c, o = _usage_of(resp)
            tot_in += i
            tot_cached += c
            tot_out += o

            calls = [item for item in (resp.output or [])
                     if getattr(item, "type", "") == "function_call"]

            if not calls:
                final_text = (getattr(resp, "output_text", "") or "").strip()
                break

            # Echo the calls back, but only the fields the API accepts as
            # input. A raw model_dump() carries `id` and `status`, which
            # are output-only and rejected with a 400.
            for call in calls:
                conversation.append({
                    "type": "function_call",
                    "call_id": call.call_id,
                    "name": call.name,
                    "arguments": call.arguments,
                })

            for call in calls:
                try:
                    args = json.loads(call.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = tools.execute(agent, call.name, args, run_id=run_id)
                if call.name == "request_approval" and result.get("ok"):
                    needs_approval = True
                conversation.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=False)[:8000],
                })
        else:
            error = f"stopped after {MAX_TURNS} turns without finishing"
    except Exception as e:
        error = f"{type(e).__name__}: {str(e)[:300]}"

    cost = _cost(model, tot_in, tot_cached, tot_out)
    status = "failed" if error else ("needs_approval" if needs_approval else "done")

    db.update("agent_runs", {"id": run_id}, {
        "status": status, "output": final_text or None, "error": error,
        "input_tokens": tot_in, "cached_tokens": tot_cached,
        "output_tokens": tot_out, "cost_usd": cost,
        "finished_at": datetime.now(timezone.utc),
    })
    try:
        db.insert("usage", {
            "agent": agent, "model": model, "run_id": run_id,
            "input_tokens": tot_in, "cached_tokens": tot_cached,
            "output_tokens": tot_out, "cost_usd": cost,
        })
    except Exception:
        pass

    return {"run_id": run_id, "agent": agent, "status": status,
            "output": final_text, "error": error,
            "input_tokens": tot_in, "cached_tokens": tot_cached,
            "output_tokens": tot_out, "cost_usd": cost}


if __name__ == "__main__":
    import sys
    who = sys.argv[1] if len(sys.argv) > 1 else "delisha"
    what = " ".join(sys.argv[2:]) or "Apa status kerja sekarang?"
    r = run(who, what)
    print(f"[{r['status']}]  ${r['cost_usd']:.5f}  "
          f"in={r['input_tokens']} cached={r['cached_tokens']} out={r['output_tokens']}")
    print()
    print(r["output"] or r["error"])
