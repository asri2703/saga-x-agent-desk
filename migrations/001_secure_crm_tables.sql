-- ============================================================
-- 001 — Stop the live leak on the existing CRM tables
-- ============================================================
-- Verified 2026-09-07: the ANON key (the one shipped to browsers)
-- could read `saga-crm-password` and `saga-resend-settings.apiKey`
-- in plaintext from both tables. RLS was off or permissive.
--
-- Run this in the Supabase SQL editor.
-- Rotate the Resend key separately — this patch cannot un-leak a
-- key that has already been exposed.
-- ============================================================

-- ── crm_data: a singleton row that holds secrets. Only the server
--    (service_role, which bypasses RLS) should read it. Enabling RLS
--    with zero policies denies anon and authenticated by default.
alter table public.crm_data enable row level security;

-- ── user_crm_data: keyed by email. Each signed-in user sees only
--    their own row. service_role still bypasses for server work.
alter table public.user_crm_data enable row level security;

drop policy if exists user_crm_data_own on public.user_crm_data;
create policy user_crm_data_own
  on public.user_crm_data
  for all
  to authenticated
  using      (user_id = auth.jwt() ->> 'email')
  with check (user_id = auth.jwt() ->> 'email');

-- ── Remove the test rows. Confirmed to hold no real data.
delete from public.user_crm_data
 where user_id in ('test@example.com', 'testing@gmail.com');

-- ── Secrets do not belong in a browser-synced blob. Strip them here;
--    they live in server env vars instead.
update public.crm_data
   set data = (data - 'saga-crm-password') - 'saga-resend-settings'
 where data ? 'saga-crm-password'
    or data ? 'saga-resend-settings';

update public.user_crm_data
   set data = data - 'saga-resend-settings'
 where data ? 'saga-resend-settings';

-- ── Verify with the ANON key afterwards: both must return 0 rows.
--    select count(*) from public.crm_data;
--    select count(*) from public.user_crm_data;
