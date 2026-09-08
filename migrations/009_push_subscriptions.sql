-- ============================================================
-- 009 — Web push subscriptions
-- ============================================================
-- One row per browser that has agreed to receive notifications. A
-- phone, an iPad and a laptop are three subscriptions for one person.
--
-- The endpoint URL is the identity: it is unique per browser per site,
-- and the push service revokes it when the user turns notifications
-- off. A 404 or 410 back from the push service means the subscription
-- is dead and should be deleted rather than retried forever.
-- ============================================================

create table if not exists desk.push_subscriptions (
  id           uuid primary key default gen_random_uuid(),
  endpoint     text not null unique,
  p256dh       text not null,
  auth         text not null,
  user_agent   text,
  label        text,
  created_at   timestamptz not null default now(),
  last_sent_at timestamptz,
  last_error   text,
  failures     integer not null default 0
);

create index if not exists push_subs_active_idx
  on desk.push_subscriptions (created_at desc);

alter table desk.push_subscriptions enable row level security;
revoke all on desk.push_subscriptions from anon, authenticated;
grant  all on desk.push_subscriptions to service_role;

-- Notifications already carry a channel; 'webpush' was in the check
-- constraint from the start, so nothing to change there.
