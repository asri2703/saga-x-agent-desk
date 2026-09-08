# Saga X Agent Desk

AI staff for **Saga X Ventures** — five agents that run the day-to-day of
two businesses, with a dashboard showing what each is doing right now.

| Agent | Role | Owns |
|---|---|---|
| **Putri** | CEO · "Hermes" on Telegram | oversight, delegation |
| **Alisya** | CTO | domains, SSL, uptime across 5 properties |
| **Julia** | CFO | clients, invoices, expenses, pricing |
| **Farah** | CMO | daily marketing, content |
| **Delisha** | COO | tasks and follow-through |

## The businesses

| | Property | Revenue shape |
|---|---|---|
| Digital marketing agency | `sagaxventures.com` | client → project → invoice |
| Hall & space rental | `space.sagaxventures.com` | booking → time slot → invoice |
| Trading signals | `masterysignal.com` | subscriber → recurring subscription |

## How it works

Abang gives an agent an instruction in plain language. The agent has real
tools against real data and carries it out. An instruction can also be
saved as a **standing assignment** that fires on a schedule
("setiap hari 9 pagi") or on an event (a domain goes down).

Permissions are tiered, and enforced in the schema rather than by asking
the model to behave:

| Action | Gate |
|---|---|
| Reads | free |
| Low-risk writes — tasks, drafts, notes | free |
| Money — invoices, pricing, payments | **approval required** |
| Outbound to a real client | **approval required** |
| Fixing broken infrastructure | **no tool exists** |

An approval stores the exact tool call and replays it verbatim when
approved, so what Abang approves is what happens.

## Stack

- **Python 3.10+**, `psycopg` and `openai` — see `requirements.txt`
- **Supabase Postgres**, schema `desk`, reached over a direct connection
  and deliberately **not** exposed to PostgREST
- **OpenAI `gpt-5.6-sol`** with prompt caching and a hard monthly cap
- Static HTML/CSS/JS, no build step

> Earlier versions of this file claimed "no pip install, no database".
> That held while the desk was a passive status board. Giving the agents
> a brain and real records ended it.

## Run locally

```bash
cp .env.example .env      # then fill it in
python -m pip install -r requirements.txt
python -m agents.preflight   # verifies setup, and that nothing leaks
python server.py             # http://localhost:8080
```

`preflight` is the one to trust. It checks behaviour, not configuration —
it makes real requests with the anon key to prove the private tables are
actually unreachable. SQL that runs without error is not the same as a
lock that holds.

## Layout

```
server.py                 HTTP server, dashboard + API
agents/
  config.py               env loading, the five agents
  db.py                   Postgres access, pinned to the desk schema
  state.py                agent state, replaces api/state.json
  prompts.py              shared business context + per-agent briefs
  tools.py                the tool surface, tiered by risk
  runner.py               model loop, per-run cost, spend cap
  chat.py                 one conversation per agent
  approvals.py            executes an approved payload verbatim
  monitors.py             Alisya's checks, incidents, honest state
  notify.py               drains notifications to Telegram
  scheduler.py            fires assignments on a clock or an event
  preflight.py            end-to-end verification
migrations/               001-007, applied in order
static/, templates/       dashboard, chat, approvals UI
deploy.sh                 one-command deploy to the VPS
```

## Operations

```bash
python -m agents.monitors     # check all properties now
python -m agents.notify       # send queued notifications
python -m agents.scheduler    # fire anything due + housekeeping
python -m agents.runner julia "Invois mana yang belum bayar?"
```

On the VPS these run from cron: scheduler every 15 min, monitors every
6 h, notifications every 5 min.

## Cost

| | |
|---|---|
| OpenAI | ~$0.015 per run, ~$13.50/month measured, capped at $30 |
| Supabase, Cloudflare | free tier at this volume |
| VPS | see `VPS_SETUP.md` |

The cap is enforced in `runner.run`, which refuses to call the model once
`desk.usage_this_month` passes `MONTHLY_CAP_USD`.

## Documents

- `PLAN.md` — the design, and what each revision got wrong
- `VPS_SETUP.md` — creating the server from scratch
- `DEPLOY.md` — nginx, TLS, systemd
- `STAFF_CHAT_BRAINSTORM.md` — superseded, kept for the personality drafts

## License

MIT
