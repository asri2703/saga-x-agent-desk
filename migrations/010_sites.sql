-- ============================================================
-- 010 — Sites an agent can build
-- ============================================================
-- Farah can already draft a caption. This lets her draft a whole site,
-- and lets Abang publish it with the same approval he uses for an
-- invoice.
--
-- The agent never runs a command. It writes rows here; approving a
-- publish copies those rows to disk. nginx is configured once, by hand,
-- to serve whatever directory matches the hostname — so publishing is
-- only ever a file write, and no agent can reload or reconfigure a web
-- server. That separation is the whole point.
-- ============================================================

create table if not exists desk.sites (
  id           uuid primary key default gen_random_uuid(),
  name         text not null,
  domain       text not null unique,
  business_id  text references desk.businesses(id),
  status       text not null default 'draft'
               check (status in ('draft','pending','live','archived')),
  brief        text,
  created_by   text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  published_at timestamptz
);

create index if not exists sites_status_idx on desk.sites (status, updated_at desc);

create table if not exists desk.site_files (
  id         uuid primary key default gen_random_uuid(),
  site_id    uuid not null references desk.sites(id) on delete cascade,
  path       text not null,
  content    text not null,
  updated_at timestamptz not null default now(),
  unique (site_id, path)
);

create index if not exists site_files_site_idx on desk.site_files (site_id, path);

alter table desk.sites      enable row level security;
alter table desk.site_files enable row level security;
revoke all on desk.sites, desk.site_files from anon, authenticated;
grant  all on desk.sites, desk.site_files to service_role;

-- What the dashboard lists without pulling every file body.
create or replace view desk.sites_overview as
  select s.id, s.name, s.domain, s.business_id, s.status, s.created_by,
         s.updated_at, s.published_at,
         count(f.id)            as file_count,
         coalesce(sum(length(f.content)), 0) as total_bytes
    from desk.sites s
    left join desk.site_files f on f.site_id = s.id
   group by s.id
   order by s.updated_at desc;
