-- ============================================================
-- 004 — Harden the `desk` schema
-- ============================================================
-- server.py connects to Postgres directly, and `desk` is deliberately
-- NOT added to Supabase's exposed schemas — so these tables are not
-- reachable over the REST API at all. Do not expose it.
--
-- This file is therefore pure defence in depth, for the day someone
-- adds `desk` to the exposed list without thinking it through:
--
--   1. GRANTS  — anon and authenticated hold no privileges here.
--                They cannot read these tables even with RLS off.
--   2. RLS     — enabled by 002 with zero policies, so it fails
--                closed if a grant is ever added by mistake.
--
-- Relying on RLS alone is exactly what leaked crm_data. One layer is
-- not enough, and neither layer costs anything to keep.
--
-- No manual dashboard step. Nothing here exposes anything.
-- ============================================================

-- ── Layer 1: grants. service_role only, everyone else revoked.

revoke all on schema desk from anon, authenticated;
grant  usage on schema desk to service_role;

revoke all on all tables    in schema desk from anon, authenticated;
revoke all on all sequences in schema desk from anon, authenticated;
revoke all on all functions in schema desk from anon, authenticated;

grant all on all tables    in schema desk to service_role;
grant all on all sequences in schema desk to service_role;
grant all on all functions in schema desk to service_role;

-- Future tables inherit the same rule, so a table added later is not
-- silently more permissive than the ones added today.
alter default privileges in schema desk
  revoke all on tables from anon, authenticated;
alter default privileges in schema desk
  revoke all on sequences from anon, authenticated;
alter default privileges in schema desk
  grant all on tables to service_role;
alter default privileges in schema desk
  grant all on sequences to service_role;

-- ── Layer 2: confirm RLS is on everywhere. 002 enables it, but this
--    is the schema's public face now, so verify rather than assume.
do $$
declare
  t record;
  missing text := '';
begin
  for t in
    select c.relname
      from pg_class c
      join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'desk'
       and c.relkind = 'r'
       and not c.relrowsecurity
  loop
    execute format('alter table desk.%I enable row level security', t.relname);
    missing := missing || t.relname || ' ';
  end loop;
  if missing <> '' then
    raise notice 'RLS was off and has been enabled on: %', missing;
  else
    raise notice 'RLS already enabled on every desk table.';
  end if;
end $$;

-- ── Verification, to run afterwards with the ANON key.
--    Every one of these must fail or return zero rows:
--      GET /rest/v1/tasks     ?select=*
--      GET /rest/v1/invoices  ?select=*
--      GET /rest/v1/services  ?select=*
--    (with header  Accept-Profile: desk)
--
--    If any of them returns data, STOP — the desk schema is public.
