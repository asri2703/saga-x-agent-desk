-- ============================================================
-- 003 — Approvals: the human-in-the-loop gate
-- ============================================================
-- Decisions this encodes:
--   * Reads are free. Low-risk writes (tasks, drafts, notes) are free.
--   * Anything touching money, pricing, or a real client goes here
--     first and waits for Abang.
--   * Outbound messages may be sent by the agent, but only after
--     one approval tap.
--
-- The point of storing the exact tool call in `payload` is that the
-- thing approved is the thing executed. The agent does not get a
-- second chance to reinterpret the instruction after you say yes.
-- ============================================================

create table if not exists desk.approvals (
  id            uuid primary key default gen_random_uuid(),
  agent         text not null,

  -- What the agent wants to do.
  action_type   text not null,
  -- One line, plain language, written for Abang to read on a phone.
  -- e.g. "Hantar invois INV-2026-014 (RM1,500) kepada Ahmad Trading"
  summary       text not null,
  -- The exact tool call, replayed verbatim on approval.
  payload       jsonb not null,

  -- Why this needed asking at all.
  risk          text not null
                check (risk in ('money','outbound','destructive','other')),

  status        text not null default 'pending'
                check (status in ('pending','approved','rejected',
                                  'executed','failed','expired')),

  -- Context so you can decide without opening another screen.
  context       text,
  client_id     uuid references desk.clients(id) on delete set null,
  amount        numeric(12,2),
  currency      text default 'MYR',

  requested_at  timestamptz not null default now(),
  decided_at    timestamptz,
  decided_via   text check (decided_via in ('dashboard','telegram')),
  executed_at   timestamptz,
  result        jsonb,
  error         text,

  -- A stale approval must not fire weeks later. Anything still
  -- pending past this is swept to 'expired' and must be re-requested.
  expires_at    timestamptz not null default (now() + interval '48 hours')
);

create index if not exists approvals_pending_idx
  on desk.approvals (status, requested_at desc)
  where status = 'pending';

create index if not exists approvals_expiry_idx
  on desk.approvals (expires_at)
  where status = 'pending';

alter table desk.approvals enable row level security;

-- Sweep stale requests. Run on the same schedule as the monitors.
create or replace function desk.expire_stale_approvals()
returns integer
language sql
as $$
  with swept as (
    update desk.approvals
       set status = 'expired', decided_at = now()
     where status = 'pending'
       and expires_at < now()
    returning 1
  )
  select count(*)::integer from swept;
$$;

-- What the dashboard and Telegram both read.
create or replace view desk.approvals_pending as
  select id, agent, action_type, summary, risk, amount, currency,
         context, requested_at, expires_at
    from desk.approvals
   where status = 'pending'
     and expires_at > now()
   order by requested_at;
