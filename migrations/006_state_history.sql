-- ============================================================
-- 006 — State history
-- ============================================================
-- Replaces api/history.jsonl, which /api/history reads today.
--
-- Two reasons this table matters beyond parity:
--
--   1. The old endpoint does readlines() on the whole file and slices
--      the tail. Fine when a human typed each entry; agents will write
--      far faster than that, and the file never rotates.
--   2. "When did Alisya last report healthy?" is a question the agents
--      need to answer, and grep over a JSONL blob is the wrong tool.
-- ============================================================

create table if not exists desk.state_history (
  id           bigserial primary key,
  agent        text not null,
  state        text not null,
  task         text default '',
  tool         text,
  -- unix seconds, matching the shape /api/history already returns so
  -- the dashboard and the Telegram bot need no changes
  ts           bigint not null,
  created_at   timestamptz not null default now()
);

create index if not exists state_history_recent_idx
  on desk.state_history (ts desc);
create index if not exists state_history_agent_idx
  on desk.state_history (agent, ts desc);

alter table desk.state_history enable row level security;

revoke all on desk.state_history from anon, authenticated;
grant all on desk.state_history to service_role;
revoke all on sequence desk.state_history_id_seq from anon, authenticated;
grant all on sequence desk.state_history_id_seq to service_role;

-- Retention. Unlike the JSONL file this replaces, something actually
-- prunes it. Run alongside the monitor sweep.
create or replace function desk.prune_state_history(keep_days integer default 180)
returns integer
language sql
as $$
  with gone as (
    delete from desk.state_history
     where created_at < now() - (keep_days || ' days')::interval
    returning 1
  )
  select count(*)::integer from gone;
$$;
