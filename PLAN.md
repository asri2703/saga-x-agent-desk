# Saga X Agent Desk — Implementation Plan

> **Rev 4 — 2026-09-07.** Supersedes `STAFF_CHAT_BRAINSTORM.md`.
>
> Earlier revisions are noted because each was wrong in an instructive way.
> Rev 1 assumed local-only JSON files. Rev 2 planned a Railway + Vercel deployment for a
> system that was **already deployed**. Rev 3 designed a schema from scratch without
> noticing a half-built CRM sitting in the same Supabase project.
> The pattern each time: planning from documents instead of checking reality.

## What this is

Abang runs **two businesses solo** and wants AI staff who do the running — not a dashboard
that displays it.

| Business | Property | Revenue shape |
|---|---|---|
| Saga X Ventures — digital marketing agency | `sagaxventures.com` | client → project → invoice |
| Saga X Space — hall & space rental | `space.sagaxventures.com` | booking → time slot → invoice |
| Mastery Signal — trading signals | `masterysignal.com` | subscriber → recurring subscription |

Signals are sold and delivered entirely through Telegram, run by **Putri** — who goes by
**Hermes** on Telegram (`@putrihermes_bot`).

## Operating model

Abang gives instructions in plain language; the staff execute. Prices, clients and services
are entered by *telling an agent*, not by filling forms — which is why every record type
needs write tools, and why `desk.services` ships empty rather than seeded with guesses.

**Permissions are tiered:**

| Action | Gate |
|---|---|
| Any read | Free |
| Low-risk writes — tasks, drafts, notes, content ideas | Free |
| Money — invoices, pricing, expenses | **Approval required** |
| Outbound — WhatsApp/email to a real client | Agent may send, **after one approval tap** |
| Incidents — something broke | **Notify only.** Agents never self-remediate |

Enforced structurally, not by prompt instruction. `desk.approvals` stores the exact tool
call and replays it verbatim on approval, so the thing approved is the thing executed — the
agent gets no second chance to reinterpret after you say yes. `desk.incidents.suggested_action`
gives an agent somewhere to write what it *would* do, with no mechanism to do it.

## The five staff

**Hermes is Putri.** "Hermes" is her name on Telegram — hence `@putrihermes_bot`. There is
no sixth agent, and no CEO/assistant boundary to draw: she is one entity wearing both hats.

| Agent | Role | Owns |
|---|---|---|
| **Putri** | CEO · "Hermes" on Telegram | Oversight across everything; delegates; flags what slipped. **Also runs the live Mastery Signal funnel** |
| **Alisya** | CTO | Monitors — domains, SSL, cron, uptime across all 5 properties |
| **Julia** | CFO | Clients, invoices, expenses, pricing, three revenue models |
| **Farah** | CMO | Daily marketing, for agency clients *and* Abang's own businesses |
| **Delisha** | COO | Tasks, follow-ups, making sure things finish |

Putri is therefore the **most sensitive agent to touch**, not the most abstract one. She is
not a new thing to build — she is a running revenue system to integrate with carefully.

## Two modes — and Rev 3 only built one

| Mode | Example | Status |
|---|---|---|
| **Reactive** — you ask | "Julia, invois client X macam mana?" | Planned since Rev 1 |
| **Proactive** — it tells you | "Abang, saga-x-crm DNS mati 3 hari" | **Added in Rev 4** |

Almost everything Abang asked for is proactive. Monitoring was marked *out of scope* in
Rev 3 — wrong, and it is the one thing actively failing today.

## Evidence this is needed

Verified live, 2026-09-07:

- Alisya's production state read `✅ 1 domains healthy`, state `idle`, while
  `saga-x-crm.com` was failing DNS resolution entirely. Silent under-reporting.
- `domain_watch.py` watched **2 of 5** properties. `space.sagaxventures.com`,
  `masterysignal.com` and the desk itself were unmonitored.
- The Supabase **anon key** — the one shipped to browsers — could read
  `saga-crm-password` in plaintext plus a live Resend API key. RLS was off.

The third is why `001` exists, and why the Resend key must be rotated regardless.

## What already exists — do not rebuild

- `desk.sagaxventures.com` — **live**. `server.py` behind Cloudflare, HTTPS active,
  63h+ uptime, deployed per `DEPLOY.md`. No Railway, no Vercel needed.
- `domain_watch.py` — the right pattern for proactive monitoring, just incomplete and mute.
- **`@putrihermes_bot`** — Putri's bot. It runs the Mastery Signal funnel *and* answers the
  desk's `/desk_*` commands (`server.py:371`). Careless webhook changes break live revenue.
  **This is the thing not to break.** See the open question about webhook ownership below.
- A half-built CRM in Supabase `public` (`crm_data`, `user_crm_data`) — clients, invoices,
  expenses, services, SST, multi-business. Nearly empty: no real clients, no real invoices,
  **no prices at all**. Absorbed into the `desk` schema rather than extended.

## Architecture

Only the inner block is new.

```
   Browser / iPad PWA · desk.sagaxventures.com   ← live, HTTPS active
            │
     ┌──────▼──────────────────┐
     │  Cloudflare  DNS + TLS  │   already configured
     └──────┬──────────────────┘
     ┌──────▼──────────────────────────────┐
     │  VPS · nginx → systemd → python     │   already running
     │   server.py                         │   existing
     │   /api/state, /api/history          │   existing
     │   /telegram/webhook/…  ← Hermes     │   existing, fragile
     │  ┌───────────────────────────────┐  │
     │  │ agents/runner.py       (new)  │  │
     │  │   OpenAI Responses API loop   │  │
     │  │ agents/tools.py        (new)  │  │
     │  │ agents/monitors.py     (new)  │  │  ← the proactive half
     │  │ /api/chat/{agent}      (new)  │  │
     │  │ /api/approvals         (new)  │  │
     │  │ usage ledger + hard cap (new) │  │
     │  └───────────────────────────────┘  │
     └──────┬──────────────────────────────┘
            │  direct Postgres — NOT PostgREST
     ┌──────▼──────────────────┐
     │  Supabase               │
     │   public.*  ← old CRM   │
     │   desk.*    ← ours      │
     └─────────────────────────┘
```

The `desk` schema is deliberately **not** exposed to PostgREST, so it is unreachable from
the internet. RLS is enabled on every table anyway — if it is ever exposed by accident it
fails closed, which is exactly the mistake that leaked the CRM tables.

## Migrations

| File | Does | Destructive? |
|---|---|---|
| `001_secure_crm_tables.sql` | RLS on the CRM tables, delete test rows, strip stored secrets | **Yes** — deletes and strips |
| `002_desk_schema.sql` | The `desk` schema: businesses, services, clients, projects, bookings, subscriptions, invoices, lines, expenses, tasks, content, monitors, checks, incidents, notifications, agent_state, messages, usage | No — creates only |
| `003_approvals.sql` | The approvals gate + expiry sweep | No — creates only |

**None have been run or syntax-checked.** Validation needs `DATABASE_URL`.

## Model & cost

OpenAI `gpt-5.6-sol` ($4 / $20 per 1M tokens). Three controls, all required:

1. **Prompt caching** — minimum cacheable prefix on GPT-5.6 is **1,024 tokens**. Below that
   it silently will not cache and the saving never arrives. Check per agent.
2. **Reasoning effort** — `low` default for routine work; raise only for real reasoning.
   A bigger lever than the choice of vendor.
3. **Hard cap** — `desk.usage` ledger and `desk.usage_this_month` view; refuse past
   `MONTHLY_CAP_USD`. Makes the budget real rather than aspirational.

**Measured**, not estimated — 4 real runs: **$0.015 per run**, cache hit rate **81%**
(one run reached 92%). At ~30 runs/day that is **~$13.50/month** against the $30 cap.
Caching was the risk here: below a 1,024-token prefix GPT-5.6 silently does not cache.
The prompts were 800-865 tokens on first draft and would have cost full price on every
call; real operational context pushed them past the line.

## Build order

- [x] **1. Migrations 001-007.** Applied and verified. 22 tables.
- [x] **2. The CRM leak.** Closed — and 001 alone did not do it. A pre-existing
      `"Allow all access"` policy made RLS meaningless, and anon held DELETE/TRUNCATE.
      Only an actual request with an actual key found that; `005` fixed it.
- [x] **3. `server.py` on Postgres.** `desk.agent_state` replaces `api/state.json`,
      response shapes byte-identical, one write path for HTTP and Telegram alike.
      Falls back to file behaviour if the agents package cannot import, so a
      half-finished deploy degrades instead of taking the desk down.
- [x] **4. Alisya.** `agents/monitors.py` — 5 properties, honest state, incidents with a
      suggested action and no way to act on it, notifications queued.
      `agents/notify.py` drains the queue to Telegram.
- [x] **5. Deployed.** GCP `saga-x-desk` (e2-small, `asia-southeast1-b`,
      Ubuntu 24.04), static IP `34.126.127.159`, no service account attached.
      nginx proxying to `server.py`, systemd unit, three cron entries, preflight
      green on the VM. DNS not cut over yet — the old server is still live.
- [x] **5b. DNS + TLS.** `desk.sagaxventures.com` now serves from the new VM behind
      Cloudflare, Let's Encrypt cert on the origin, HTTP redirects to HTTPS. Needs: `pip install -r requirements.txt`,
      `DATABASE_URL` in the systemd unit, `TG_ALLOWED_CHAT_IDS`, `import_legacy()` run
      there, and two cron entries. **This is where VPS access is needed.**
- [ ] **6. Measure** a week before adding more agents.
- [x] **7. The runner.** `agents/runner.py`, `tools.py`, `prompts.py`. Verified with real
      calls: agents read real data, reply in the language asked, refuse to invent prices,
      and money requests queue an approval instead of executing.
- [x] **8. Chat + approvals in the dashboard.** `agents/approvals.py` executes an approved
      payload verbatim; `agents/chat.py` keeps one conversation per agent. New routes:
      `GET/POST /api/chat/{agent}`, `GET /api/approvals`,
      `POST /api/approvals/{id}/approve|reject`. Tabbed UI in `chat.js` / `chat.css`.
      Verified: approving a queued invoice created a real `INV-2026-001` with its line
      item, SST correctly at 0, status `draft` — sending is a separate approval.
- [x] **9. The scheduler.** `agents/scheduler.py`. Fires only assignments Abang wrote —
      it cannot invent, reword, or decide work deserves doing. Three brakes:
      `SCHEDULER_ENABLED`, per-assignment `enabled`, and the monthly cap.
      Agents can set up a standing instruction via `create_assignment`, so scheduling
      happens by telling them, not by editing a config. Event triggers fire from the
      monitors the moment an incident opens.
      Schedules compute in `Asia/Kuala_Lumpur` — computing in UTC would have made
      "setiap hari 9 pagi" arrive at 5pm.
- [ ] **10. Delisha → Julia → Farah.** Julia is largest: three revenue models + approvals.
- [ ] **11. Putri last** — she reads across the others *and* runs the live sales funnel.
- [ ] **12. PWA push.** HTTPS is already there; Telegram works first.

## Open

**To do when the project is finished**

- **Delete the GCP service account key.** `desk-deployer` in project `desk-sagax`.
  The VM is built and deploys now run over SSH, so the key has no remaining use —
  it is a long-lived credential earning nothing. Console → IAM → Service Accounts
  → Keys → delete.

**Blocking deployment**

- Nothing. Deployed and live.

**Answered, kept for the record**

- **The Telegram webhook.** `getWebhookInfo` returns no webhook at all. So
  `server.py`'s `/telegram/webhook/{secret}` is never called and `/desk_*` over
  webhook is dead code today. The funnel must therefore be polling — which means
  **setting a webhook on this bot would kill the funnel instantly.** One bot, one
  delivery method.

**Still unresolved**

- **Where the funnel code lives.** Not in this repo. Needed before touching Telegram.
- **`saga-x-crm.com`** — dead DNS, now monitored and opening incidents. Fix it, or
  disable the monitor. Leaving it failing trains Abang to ignore Alisya, which
  defeats the point of her.
- **Prices.** `services` is empty. Agents will refuse to quote until it is filled,
  which is correct behaviour but limits what Julia can do.
