"""
Saga X Agent Desk — preflight check
===================================
    python -m agents.preflight

Verifies the setup end to end. The security section is the point of
this file: SQL running without error is not the same as a lock
holding. Migration 001 enabled RLS, reported success, and the anon key
could still read everything — a pre-existing "Allow all access" policy
made RLS meaningless. Only an actual request with an actual key found
that. So this checks behaviour, never configuration.

Prints no secrets. Exit 0 = ready, 1 = something needs attention.
"""

import json
import sys
import urllib.error
import urllib.request

from . import config, db

OK = "  [ OK ]"
NO = "  [FAIL]"
WARN = "  [warn]"

EXPECTED_TABLES = [
    "businesses", "services", "clients", "projects", "bookings",
    "subscriptions", "invoices", "invoice_lines", "expenses", "tasks",
    "content", "monitors", "monitor_checks", "incidents",
    "notifications", "agent_state", "messages", "usage", "approvals",
    "state_history", "assignments", "agent_runs",
]

failures: list[str] = []
warnings: list[str] = []


def fail(msg: str, fix: str = "") -> None:
    print(f"{NO} {msg}")
    if fix:
        print(f"         fix: {fix}")
    failures.append(msg)


def warn(msg: str) -> None:
    print(f"{WARN} {msg}")
    warnings.append(msg)


def section(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def _rest_get(path: str, key: str, profile: str | None = None):
    """Returns (status, parsed_or_text). Used only to prove that things
    which should be unreachable actually are."""
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    if profile:
        headers["Accept-Profile"] = profile
    url = f"{config.SUPABASE_URL}/rest/v1/{path}"
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers), timeout=20) as r:
            body = r.read()
            return r.status, (json.loads(body) if body else [])
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


# ── 1 ───────────────────────────────────────────────────────────
def check_config() -> None:
    section("1. Configuration")
    for key, present in config.health().items():
        if present:
            print(f"{OK} {key}")
        elif key in ("telegram_bot_token", "telegram_allowlist"):
            warn(f"{key} not set — Telegram notifications will not send")
        elif key == "openai_api_key":
            warn(f"{key} not set — agents cannot call the model yet")
        else:
            fail(f"{key} not set", "add it to .env (see .env.example)")
    if not config.get("DATABASE_URL"):
        fail("DATABASE_URL not set",
             "Supabase > Settings > Database > Connection string > URI")
    else:
        print(f"{OK} database_url")
    print(f"{OK} model={config.OPENAI_MODEL} effort={config.OPENAI_REASONING_EFFORT} "
          f"cap=${config.MONTHLY_CAP_USD:.2f}")


# ── 2 ───────────────────────────────────────────────────────────
def check_database() -> None:
    section("2. Postgres reachable, schema pinned")
    try:
        print(f"{OK} {db.ping()}")
    except Exception as e:
        fail(f"cannot connect: {str(e).splitlines()[0][:160]}")
        return
    try:
        path = db.query("show search_path")[0]
        val = list(path.values())[0]
        if "desk" in val and "public" not in val:
            print(f"{OK} search_path = {val}  (public not on the path)")
        else:
            warn(f"search_path = {val} — an unqualified name could hit public")
    except Exception as e:
        warn(f"search_path check failed: {e}")

    missing = [t for t in EXPECTED_TABLES
               if not db.query("""select 1 from information_schema.tables
                                  where table_schema='desk' and table_name=%s""", [t])]
    if missing:
        fail(f"{len(missing)} table(s) missing: {', '.join(missing)}",
             "re-run migrations 002 and 003")
    else:
        print(f"{OK} all {len(EXPECTED_TABLES)} desk tables present")


# ── 3. THE SECURITY SECTION ─────────────────────────────────────
def check_not_exposed() -> None:
    section("3. Security — behaviour, not configuration")

    # 3a. desk must be unreachable over REST for EVERY key, including
    #     service_role. Not exposed at all beats exposed but locked.
    exposed = []
    for key_name, key in (("anon", config.SUPABASE_ANON_KEY),
                          ("service_role", config.SUPABASE_SERVICE_ROLE_KEY)):
        if not key:
            warn(f"{key_name} key not set — cannot check")
            continue
        status, body = _rest_get("agent_state?select=agent&limit=1", key, "desk")
        if status == 200 and isinstance(body, list):
            exposed.append(key_name)
            print(f"{NO} desk reachable over REST with the {key_name} key")
        elif isinstance(body, str) and "PGRST106" in body:
            print(f"{OK} desk not exposed to PostgREST ({key_name}: HTTP {status})")
        else:
            print(f"{OK} desk blocked for {key_name} (HTTP {status})")
    if exposed:
        fail(f"desk schema is served over REST ({', '.join(exposed)})",
             "remove `desk` from Supabase > Settings > API > Exposed schemas")

    # 3b. the CRM tables that leaked must stay shut to anon.
    if config.SUPABASE_ANON_KEY:
        for table in ("crm_data", "user_crm_data"):
            status, body = _rest_get(f"{table}?select=*", config.SUPABASE_ANON_KEY)
            if status == 200 and isinstance(body, list) and body:
                fail(f"anon can still read public.{table} ({len(body)} rows)",
                     "re-run migration 005")
            elif status == 200:
                print(f"{OK} public.{table}: anon allowed but 0 rows (RLS holding)")
            else:
                print(f"{OK} public.{table}: anon rejected (HTTP {status})")

    # 3c. no policy may hand `public` the whole table again.
    try:
        loose = db.query("""select tablename, policyname, roles::text
                              from pg_policies
                             where schemaname='public' and qual='true'
                               and roles::text like '%public%'""")
        if loose:
            for p in loose:
                fail(f"permissive policy {p['tablename']}.{p['policyname']} "
                     f"grants {p['roles']} everything")
        else:
            print(f"{OK} no allow-everything policies remain in public")
    except Exception as e:
        warn(f"policy audit failed: {e}")


# ── 4 ───────────────────────────────────────────────────────────
def check_seeds() -> None:
    section("4. Seed data")
    try:
        biz = {b["id"] for b in db.select("businesses", columns="id")}
        for want in ("agency", "space", "signals"):
            if want in biz:
                print(f"{OK} business '{want}'")
            else:
                fail(f"business '{want}' missing")

        agents = {a["agent"] for a in db.select("agent_state", columns="agent")}
        for a in config.AGENTS:
            if a not in agents:
                fail(f"agent_state row missing: {a}")
        extra = agents - set(config.AGENTS)
        if extra:
            warn(f"unexpected agent rows: {sorted(extra)}")
        else:
            print(f"{OK} all {len(config.AGENTS)} agents seeded")

        targets = {m["target"] for m in db.select("monitors", columns="target")}
        print(f"{OK} {len(targets)} monitor(s) configured")
        for want in ("sagaxventures.com", "space.sagaxventures.com",
                     "masterysignal.com", "desk.sagaxventures.com"):
            if want not in targets:
                warn(f"not monitored: {want}")

        if db.count("services") == 0:
            warn("services table is empty — agents cannot quote prices yet")
        else:
            print(f"{OK} {db.count('services')} service(s) priced")
    except Exception as e:
        fail(f"seed check failed: {str(e)[:200]}")


# ── 5 ───────────────────────────────────────────────────────────
def check_ledger() -> None:
    section("5. Spend ledger")
    try:
        allowed, spent, cap = db.under_cap()
        state = "under" if allowed else "OVER — calls will be refused"
        print(f"{OK} month-to-date ${spent:.2f} of ${cap:.2f} cap ({state})")
    except Exception as e:
        fail(f"usage_this_month unreadable: {str(e)[:160]}", "re-run migration 002")


def main() -> int:
    print("Saga X Agent Desk — preflight")
    print(f"project: {config.SUPABASE_URL or '(SUPABASE_URL not set)'}")
    check_config()
    check_database()
    check_not_exposed()
    check_seeds()
    check_ledger()

    print("\n" + "=" * 54)
    if failures:
        print(f"{len(failures)} problem(s):")
        for f in failures:
            print(f"  - {f}")
    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")
    if not failures:
        print("Ready." if not warnings else "Ready, with warnings above.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
