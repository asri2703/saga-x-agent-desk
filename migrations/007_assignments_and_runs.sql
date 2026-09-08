-- ============================================================
-- 007 — Assignments and runs
-- ============================================================
-- The operating model: Abang hands a staff member an assignment, and
-- the assignment itself triggers the work. Not a chat window he has to
-- sit in — an instruction that fires.
--
-- Three trigger kinds, because all three were asked for:
--   manual    "Julia, siapkan invois untuk Ahmad"      — fires once, now
--   schedule  "buat marketing setiap hari"             — fires on a clock
--   event     "beritahu bila ada domain mati"          — fires on a signal
--
-- `assignments` is the standing instruction. `agent_runs` is one
-- execution of it. Separating them is what makes a daily assignment
-- possible, and what lets us answer "which assignment is eating the
-- budget" instead of only "how much did we spend".
-- ============================================================

create table if not exists desk.assignments (
  id            uuid primary key default gen_random_uuid(),
  agent         text not null,
  title         text not null,
  -- The brief, in Abang's own words. This is what the agent is given;
  -- it is not a template or a slug, and it is deliberately free text.
  instruction   text not null,
  business_id   text references desk.businesses(id),

  trigger_kind  text not null default 'manual'
                check (trigger_kind in ('manual','schedule','event')),

  -- schedule triggers
  schedule_kind text check (schedule_kind in ('hourly','daily','weekly','monthly')),
  schedule_at   time,                    -- local time of day to fire
  schedule_dow  integer check (schedule_dow between 0 and 6),  -- weekly
  schedule_dom  integer check (schedule_dom between 1 and 28), -- monthly

  -- event triggers: which signal wakes this up
  event_type    text check (event_type in ('monitor_down','monitor_recovered',
                                           'ssl_expiring','invoice_overdue',
                                           'booking_upcoming','subscription_renewing')),

  enabled       boolean not null default true,
  last_run_at   timestamptz,
  next_run_at   timestamptz,
  run_count     integer not null default 0,

  -- Highest reasoning effort this assignment may use. Routine daily
  -- work should not quietly run at `high` and drain the month's budget.
  max_effort    text not null default 'low'
                check (max_effort in ('minimal','low','medium','high','max')),

  notes         text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index if not exists assignments_due_idx
  on desk.assignments (next_run_at)
  where enabled and trigger_kind = 'schedule';
create index if not exists assignments_event_idx
  on desk.assignments (event_type)
  where enabled and trigger_kind = 'event';
create index if not exists assignments_agent_idx
  on desk.assignments (agent, enabled);


-- ── One execution ───────────────────────────────────────────────
create table if not exists desk.agent_runs (
  id            uuid primary key default gen_random_uuid(),
  assignment_id uuid references desk.assignments(id) on delete set null,
  agent         text not null,

  -- 'chat' covers ad-hoc conversation, which has no assignment behind
  -- it but still costs money and still deserves a record.
  trigger_kind  text not null default 'manual'
                check (trigger_kind in ('manual','schedule','event','chat')),
  trigger_detail text,                   -- e.g. the incident id that fired it

  -- Snapshot of the instruction as given. Editing an assignment later
  -- must not rewrite the history of what was actually asked.
  instruction   text,

  status        text not null default 'queued'
                check (status in ('queued','running','needs_approval',
                                  'done','failed','cancelled')),
  output        text,
  error         text,

  -- Per-run cost. This is what makes "which assignment is expensive"
  -- answerable; desk.usage alone only gives a monthly total.
  model         text,
  effort        text,
  input_tokens  integer not null default 0,
  cached_tokens integer not null default 0,
  output_tokens integer not null default 0,
  cost_usd      numeric(10,6) not null default 0,

  queued_at     timestamptz not null default now(),
  started_at    timestamptz,
  finished_at   timestamptz
);

create index if not exists runs_pending_idx
  on desk.agent_runs (status, queued_at)
  where status in ('queued','running','needs_approval');
create index if not exists runs_agent_idx on desk.agent_runs (agent, queued_at desc);
create index if not exists runs_assignment_idx
  on desk.agent_runs (assignment_id, queued_at desc);


-- ── Wire the existing tables to runs ────────────────────────────
-- An approval belongs to the run that asked for it, so approving one
-- can resume exactly that run rather than guessing.
alter table desk.approvals
  add column if not exists run_id uuid references desk.agent_runs(id) on delete set null;

-- Spend becomes attributable, not just countable.
alter table desk.usage
  add column if not exists run_id uuid references desk.agent_runs(id) on delete set null;

-- A run that produced a task should be traceable from it.
alter table desk.tasks
  add column if not exists created_by_run uuid references desk.agent_runs(id) on delete set null;


-- ── Security, same as every other desk table ────────────────────
alter table desk.assignments enable row level security;
alter table desk.agent_runs  enable row level security;

revoke all on desk.assignments, desk.agent_runs from anon, authenticated;
grant  all on desk.assignments, desk.agent_runs to service_role;


-- ── What the scheduler polls ────────────────────────────────────
create or replace view desk.assignments_due as
  select id, agent, title, instruction, business_id, max_effort, next_run_at
    from desk.assignments
   where enabled
     and trigger_kind = 'schedule'
     and next_run_at is not null
     and next_run_at <= now()
   order by next_run_at;

-- What the dashboard shows as "in flight".
create or replace view desk.runs_active as
  select r.id, r.agent, r.status, r.trigger_kind, r.instruction,
         r.queued_at, r.started_at, a.title as assignment_title
    from desk.agent_runs r
    left join desk.assignments a on a.id = r.assignment_id
   where r.status in ('queued','running','needs_approval')
   order by r.queued_at;
