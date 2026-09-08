-- ============================================================
-- 002 — The `desk` schema
-- ============================================================
-- Absorbs the half-built CRM model (clients, invoices, expenses,
-- services, tasks, SST) and adds the proactive half the old plan
-- was missing: monitors, incidents, notifications.
--
-- Lives in its own schema, NOT `public`, so it can never collide
-- with the existing crm_data / user_crm_data tables.
--
-- Deliberately NOT exposed to PostgREST. server.py connects to
-- Postgres directly, so these tables are unreachable from the
-- internet. RLS below is defence in depth, not the only lock.
-- ============================================================

create schema if not exists desk;

-- ============================================================
-- Reference: the three businesses
-- ============================================================
-- Each has a genuinely different revenue shape, which is why
-- projects / bookings / subscriptions are separate tables rather
-- than one polymorphic table with mostly-null columns. Explicit
-- names also make the agent tools far harder to misuse.

create table if not exists desk.businesses (
  id          text primary key,           -- 'agency' | 'space' | 'signals'
  name        text not null,
  domain      text,
  notes       text,
  created_at  timestamptz not null default now()
);

insert into desk.businesses (id, name, domain) values
  ('agency',  'Saga X Ventures — Digital Marketing', 'sagaxventures.com'),
  ('space',   'Saga X Space — Hall & Space Rental',  'space.sagaxventures.com'),
  ('signals', 'Mastery Signal',                      'masterysignal.com')
on conflict (id) do nothing;

-- ============================================================
-- Pricing — what the agents need to quote correctly
-- ============================================================
-- The old CRM had saga-services: [] and only generic svc-types
-- ("Service", "Product", "Subscription"). No actual prices existed
-- anywhere. This table is the place for them; it starts empty and
-- must be filled before any agent can quote a real number.

create table if not exists desk.services (
  id            uuid primary key default gen_random_uuid(),
  business_id   text not null references desk.businesses(id),
  name          text not null,
  description   text,
  kind          text not null default 'service'
                check (kind in ('service','product','subscription')),
  unit_price    numeric(12,2) not null,
  currency      text not null default 'MYR',
  unit          text not null default 'per_project'
                check (unit in ('per_project','per_month','per_hour','per_day',
                                'per_booking','per_item','per_campaign')),
  -- subscriptions only: how often it renews
  billing_period text check (billing_period in ('monthly','quarterly','yearly')),
  active        boolean not null default true,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index if not exists services_biz_idx on desk.services (business_id, active);

-- ============================================================
-- Clients
-- ============================================================
-- WhatsApp is a first-class field — the old CRM task blob already
-- carried one, and it is how business actually gets done here.

create table if not exists desk.clients (
  id           uuid primary key default gen_random_uuid(),
  business_id  text references desk.businesses(id),
  name         text not null,
  company      text,
  email        text,
  phone        text,
  whatsapp     text,
  status       text not null default 'active'
               check (status in ('lead','active','dormant','lost')),
  source       text,
  notes        text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index if not exists clients_status_idx on desk.clients (status, business_id);

-- ============================================================
-- Three revenue shapes
-- ============================================================

-- Agency: scoped work with a start and an end.
create table if not exists desk.projects (
  id           uuid primary key default gen_random_uuid(),
  client_id    uuid references desk.clients(id) on delete set null,
  name         text not null,
  description  text,
  status       text not null default 'proposed'
               check (status in ('proposed','active','on_hold','delivered','cancelled')),
  started_on   date,
  due_on       date,
  delivered_on date,
  quoted_total numeric(12,2),
  currency     text not null default 'MYR',
  notes        text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index if not exists projects_status_idx on desk.projects (status, due_on);

-- Space rental: a slot in time, not a project.
create table if not exists desk.bookings (
  id           uuid primary key default gen_random_uuid(),
  client_id    uuid references desk.clients(id) on delete set null,
  space_name   text not null,
  starts_at    timestamptz not null,
  ends_at      timestamptz not null,
  headcount    integer,
  status       text not null default 'pending'
               check (status in ('enquiry','pending','confirmed','completed','cancelled','no_show')),
  quoted_total numeric(12,2),
  currency     text not null default 'MYR',
  notes        text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  constraint bookings_time_order check (ends_at > starts_at)
);
create index if not exists bookings_time_idx on desk.bookings (starts_at, status);

-- Signals: recurring, sold and delivered through Telegram.
create table if not exists desk.subscriptions (
  id              uuid primary key default gen_random_uuid(),
  client_id       uuid references desk.clients(id) on delete set null,
  service_id      uuid references desk.services(id),
  telegram_user   text,                    -- how Hermes identifies them
  telegram_chat_id bigint,
  status          text not null default 'active'
                  check (status in ('trial','active','past_due','cancelled','expired')),
  started_on      date not null default current_date,
  renews_on       date,
  cancelled_on    date,
  amount          numeric(12,2),
  currency        text not null default 'MYR',
  notes           text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index if not exists subs_renew_idx on desk.subscriptions (status, renews_on);

-- ============================================================
-- Money
-- ============================================================
-- SST defaults to 6% and disabled, matching the CRM's tax settings.
-- An invoice can hang off any one of the three revenue shapes.

create table if not exists desk.invoices (
  id            uuid primary key default gen_random_uuid(),
  business_id   text not null references desk.businesses(id),
  client_id     uuid references desk.clients(id) on delete set null,
  project_id    uuid references desk.projects(id) on delete set null,
  booking_id    uuid references desk.bookings(id) on delete set null,
  subscription_id uuid references desk.subscriptions(id) on delete set null,
  number        text unique not null,
  status        text not null default 'draft'
                check (status in ('draft','sent','partial','paid','overdue','void')),
  issued_on     date not null default current_date,
  due_on        date,
  currency      text not null default 'MYR',
  subtotal      numeric(12,2) not null default 0,
  tax_rate      numeric(5,2)  not null default 6.00,   -- SST
  tax_enabled   boolean       not null default false,
  tax_amount    numeric(12,2) not null default 0,
  total         numeric(12,2) not null default 0,
  amount_paid   numeric(12,2) not null default 0,
  paid_at       timestamptz,
  notes         text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index if not exists invoices_status_idx on desk.invoices (status, due_on);
create index if not exists invoices_client_idx on desk.invoices (client_id);

create table if not exists desk.invoice_lines (
  id          uuid primary key default gen_random_uuid(),
  invoice_id  uuid not null references desk.invoices(id) on delete cascade,
  service_id  uuid references desk.services(id),
  description text not null,
  qty         numeric(10,2) not null default 1,
  unit_price  numeric(12,2) not null,
  line_total  numeric(12,2) generated always as (qty * unit_price) stored,
  position    integer not null default 0
);
create index if not exists invoice_lines_inv_idx on desk.invoice_lines (invoice_id, position);

create table if not exists desk.expenses (
  id           uuid primary key default gen_random_uuid(),
  business_id  text references desk.businesses(id),
  description  text not null,
  category     text,
  amount       numeric(12,2) not null,
  currency     text not null default 'MYR',
  spent_on     date not null default current_date,
  recurring    boolean not null default false,
  notes        text,
  created_at   timestamptz not null default now()
);
create index if not exists expenses_date_idx on desk.expenses (spent_on desc);

-- ============================================================
-- Work
-- ============================================================
-- Mirrors the old CRM task blob: biz, category, priority, status,
-- date, reminder, client link, invoice link.

create table if not exists desk.tasks (
  id           uuid primary key default gen_random_uuid(),
  business_id  text references desk.businesses(id),
  title        text not null,
  description  text,
  owner        text,                        -- agent id, or 'abang'
  category     text,
  priority     text not null default 'med' check (priority in ('low','med','high','urgent')),
  status       text not null default 'todo'
               check (status in ('todo','in_progress','blocked','done','cancelled')),
  due_on       date,
  remind       boolean not null default false,
  client_id    uuid references desk.clients(id) on delete set null,
  invoice_id   uuid references desk.invoices(id) on delete set null,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  completed_at timestamptz
);
create index if not exists tasks_open_idx on desk.tasks (status, due_on) where status <> 'done';

-- Marketing output. Buffer publishing stays on hold, so `external_ref`
-- is the seam a Buffer post id drops into later.
create table if not exists desk.content (
  id           uuid primary key default gen_random_uuid(),
  business_id  text references desk.businesses(id),
  client_id    uuid references desk.clients(id) on delete set null,
  title        text not null,
  body         text,
  channel      text check (channel in ('facebook','instagram','tiktok','telegram',
                                       'linkedin','x','email','blog','other')),
  status       text not null default 'idea'
               check (status in ('idea','drafting','review','scheduled','published','archived')),
  publish_at   timestamptz,
  published_at timestamptz,
  external_ref text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index if not exists content_sched_idx on desk.content (status, publish_at);

-- ============================================================
-- The proactive half — monitoring, incidents, notifications
-- ============================================================
-- This is what the old plan was missing entirely. Alisya currently
-- watches 2 domains and reported "1 domains healthy" with a green
-- tick while saga-x-crm.com was failing DNS. Silent under-reporting
-- is the bug this section exists to kill.

create table if not exists desk.monitors (
  id             uuid primary key default gen_random_uuid(),
  name           text not null,
  kind           text not null default 'https'
                 check (kind in ('https','dns','ssl','cron','telegram_bot','custom')),
  target         text not null,             -- domain, url, or cron job name
  business_id    text references desk.businesses(id),
  owner_agent    text not null default 'alisya',
  interval_mins  integer not null default 360,
  -- consecutive failures before an incident opens; stops flapping alerts
  fail_threshold integer not null default 2,
  warn_days_left integer default 14,        -- SSL expiry warning window
  enabled        boolean not null default true,
  created_at     timestamptz not null default now(),
  -- Without this, re-running the migration duplicates every seed row.
  constraint monitors_kind_target_uniq unique (kind, target)
);

-- Seed every live property. The old config watched 2 of 5 and did
-- not watch the desk itself.
insert into desk.monitors (name, kind, target, business_id) values
  ('Saga X main site',   'https', 'sagaxventures.com',       'agency'),
  ('Saga X space',       'https', 'space.sagaxventures.com', 'space'),
  ('Mastery Signal',     'https', 'masterysignal.com',       'signals'),
  ('Agent Desk (self)',  'https', 'desk.sagaxventures.com',  'agency')
on conflict (kind, target) do nothing;

create table if not exists desk.monitor_checks (
  id           bigserial primary key,
  monitor_id   uuid not null references desk.monitors(id) on delete cascade,
  checked_at   timestamptz not null default now(),
  ok           boolean not null,
  http_status  integer,
  response_ms  integer,
  ssl_days_left integer,
  resolved_ip  text,
  error        text
);
create index if not exists checks_recent_idx on desk.monitor_checks (monitor_id, checked_at desc);
-- Retention: this table grows forever otherwise. Prune on a schedule —
--   delete from desk.monitor_checks where checked_at < now() - interval '90 days';

create table if not exists desk.incidents (
  id            uuid primary key default gen_random_uuid(),
  monitor_id    uuid references desk.monitors(id) on delete set null,
  title         text not null,
  detail        text,
  severity      text not null default 'warning'
                check (severity in ('info','warning','critical')),
  status        text not null default 'open'
                check (status in ('open','acknowledged','resolved')),
  -- Agents NEVER auto-remediate. They write what they would suggest
  -- here; Abang decides. This column is the whole "notify first" rule
  -- made structural rather than a line in a prompt.
  suggested_action text,
  opened_at     timestamptz not null default now(),
  acknowledged_at timestamptz,
  resolved_at   timestamptz
);
create index if not exists incidents_open_idx on desk.incidents (status, severity, opened_at desc);

create table if not exists desk.notifications (
  id          uuid primary key default gen_random_uuid(),
  incident_id uuid references desk.incidents(id) on delete cascade,
  agent       text,
  channel     text not null default 'telegram'
              check (channel in ('telegram','webpush','email')),
  title       text,
  body        text not null,
  sent_at     timestamptz,
  delivered   boolean not null default false,
  error       text,
  created_at  timestamptz not null default now()
);
create index if not exists notif_pending_idx on desk.notifications (delivered, created_at);

-- ============================================================
-- Agent infrastructure
-- ============================================================

-- Replaces api/state.json. Column names match the JSON keys exactly
-- so /api/state can keep its current response shape and the existing
-- dashboard + Telegram bot carry on working untouched.
create table if not exists desk.agent_state (
  agent        text primary key,
  name         text not null,
  role         text not null,
  state        text not null default 'idle'
               check (state in ('idle','thinking','working','done','error','offline')),
  task         text default '',
  current_tool text,
  updated_at   bigint                       -- unix seconds, as today
);

-- Five agents. "Hermes" is Putri's name on Telegram, not a sixth
-- agent — hence @putrihermes_bot. She is CEO, overall assistant, and
-- the one running the Mastery Signal funnel.
insert into desk.agent_state (agent, name, role, task) values
  ('putri',   'Putri',   'CEO',  'Awaiting orders'),
  ('alisya',  'Alisya',  'CTO',  'Idle'),
  ('julia',   'Julia',   'CFO',  'Idle'),
  ('farah',   'Farah',   'CMO',  'Idle'),
  ('delisha', 'Delisha', 'COO',  'Idle')
on conflict (agent) do nothing;

-- Per-agent chat history, one row per message.
create table if not exists desk.messages (
  id          bigserial primary key,
  agent       text not null,
  role        text not null check (role in ('user','assistant','tool','system')),
  content     text,
  tool_name   text,
  tool_args   jsonb,
  created_at  timestamptz not null default now()
);
create index if not exists messages_agent_idx on desk.messages (agent, created_at desc);

-- The spend ledger. The hard cap reads this before every API call.
create table if not exists desk.usage (
  id             bigserial primary key,
  agent          text,
  model          text not null,
  input_tokens   integer not null default 0,
  cached_tokens  integer not null default 0,
  output_tokens  integer not null default 0,
  cost_usd       numeric(10,6) not null default 0,
  created_at     timestamptz not null default now()
);
create index if not exists usage_month_idx on desk.usage (created_at desc);

-- Month-to-date spend — what the cap checks.
create or replace view desk.usage_this_month as
  select coalesce(sum(cost_usd), 0)::numeric(10,2) as spent_usd,
         count(*)                                  as calls
    from desk.usage
   where created_at >= date_trunc('month', now());

-- ============================================================
-- RLS — defence in depth
-- ============================================================
-- server.py connects as a role that bypasses RLS, and this schema is
-- not exposed to PostgREST, so nothing here is internet-reachable.
-- Enabling RLS with no policies means that if the schema is ever
-- exposed by accident, it fails closed instead of open — which is
-- exactly the mistake that leaked the CRM tables.

do $$
declare t record;
begin
  for t in
    select tablename from pg_tables where schemaname = 'desk'
  loop
    execute format('alter table desk.%I enable row level security', t.tablename);
  end loop;
end $$;
