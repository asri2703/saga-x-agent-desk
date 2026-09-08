-- ============================================================
-- 005 — Actually close the CRM leak
-- ============================================================
-- 001 enabled RLS on crm_data and user_crm_data and reported success,
-- but the anon key could still read both. Verification found why:
--
--   policy "Allow all access"  PERMISSIVE  roles={public}  ALL  USING (true)
--
-- RLS with a policy that says "allow everyone everything" is not a
-- lock. On top of that, anon held INSERT/UPDATE/DELETE/TRUNCATE — so
-- anyone with the anon key could have emptied the CRM, not merely
-- read it.
--
-- 001 missed this because it enabled RLS without auditing the policies
-- that were already there. Enabling RLS is not the same as denying.
-- ============================================================

-- ── The policy that made RLS meaningless.
drop policy if exists "Allow all access" on public.crm_data;
drop policy if exists "Allow all access" on public.user_crm_data;

-- ── crm_data holds the singleton config row. Nothing client-side has
--    any business touching it. service_role bypasses RLS, so the
--    server keeps working with no policy at all.
revoke all on public.crm_data from anon, authenticated;

-- ── user_crm_data is per-user. authenticated users may work with
--    their own row and nothing else; the policy from 001 enforces the
--    row scope, and these grants remove the ability to drop the table
--    contents wholesale.
revoke all on public.user_crm_data from anon, authenticated;
grant select, insert, update on public.user_crm_data to authenticated;

-- anon gets nothing on either table. If the CRM app at saga-x-crm.com
-- is ever revived it must sign in rather than rely on the anon key —
-- which is the correct design for data keyed by user email anyway.

-- ── Verify afterwards. Both must return zero rows with the anon key:
--      GET /rest/v1/crm_data?select=*
--      GET /rest/v1/user_crm_data?select=*
--
--   select tablename, policyname, roles, qual from pg_policies
--    where schemaname = 'public';
--   -- expect only user_crm_data_own, scoped to authenticated
