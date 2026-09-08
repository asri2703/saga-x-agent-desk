"""
Saga X Agent Desk — Postgres access for the `desk` schema
=========================================================
server.py connects to Postgres directly. The `desk` schema is NOT in
Supabase's exposed-schemas list, so these tables cannot be reached
over the REST API at all — that is the point, and it is why we went
back to a direct connection after the CRM leak.

search_path is pinned to `desk` alone. An unqualified table name that
does not exist in `desk` therefore fails loudly instead of silently
resolving to something in `public` — where the old CRM lives.

Connection handling: ThreadingHTTPServer serves requests concurrently,
so connections are pooled through a small queue rather than shared.
The pool is deliberately tiny; this is a single-operator desk, and
Supabase caps direct connections.
"""

from __future__ import annotations

import queue
import threading
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from . import config

POOL_SIZE = 4
_pool: queue.Queue[psycopg.Connection] = queue.Queue(maxsize=POOL_SIZE)
_lock = threading.Lock()
_created = 0


class DBError(RuntimeError):
    pass


def _connect() -> psycopg.Connection:
    dsn = config.get("DATABASE_URL")
    if not dsn:
        raise DBError(
            "DATABASE_URL is not set. Supabase > Settings > Database > "
            "Connection string > URI, with the password filled in."
        )
    conn = psycopg.connect(dsn, connect_timeout=15, row_factory=dict_row,
                           autocommit=True)
    # Pin the schema. Nothing here should ever touch `public` by accident.
    conn.execute("set search_path to desk")
    return conn


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    """Borrow a connection. Dead ones are replaced rather than reused —
    Supabase closes idle connections, and a stale handle otherwise
    surfaces as a confusing error at the call site."""
    global _created
    try:
        conn = _pool.get_nowait()
    except queue.Empty:
        with _lock:
            if _created < POOL_SIZE:
                _created += 1
                conn = _connect()
            else:
                conn = _pool.get(timeout=30)

    if conn.closed:
        conn = _connect()

    try:
        yield conn
    except psycopg.OperationalError:
        # Connection is suspect; drop it rather than return it to the pool.
        try:
            conn.close()
        except Exception:
            pass
        with _lock:
            _created -= 1
        raise
    else:
        try:
            _pool.put_nowait(conn)
        except queue.Full:
            conn.close()
            with _lock:
                _created -= 1


# ── Raw ─────────────────────────────────────────────────────────

def query(statement: str | sql.Composed, params: Any = None) -> list[dict]:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(statement, params)
            if cur.description is None:
                return []
            return cur.fetchall()


def execute(statement: str | sql.Composed, params: Any = None) -> int:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(statement, params)
            return cur.rowcount


# ── Filter helper ───────────────────────────────────────────────
# Filters are {column: value} for equality, or {column: (op, value)}
# for anything else — ("gte", 100), ("in", [...]), ("is", None).

_ALLOWED_OPS = {"=", "!=", "<", "<=", ">", ">=", "like", "ilike", "in", "is"}


def _where(filters: dict[str, Any] | None) -> tuple[sql.Composed, list]:
    if not filters:
        return sql.SQL(""), []
    clauses, params = [], []
    for col, val in filters.items():
        if isinstance(val, tuple) and len(val) == 2:
            op, v = val
            op = str(op).lower()
            if op not in _ALLOWED_OPS:
                raise DBError(f"operator not allowed: {op!r}")
        else:
            op, v = ("is", None) if val is None else ("=", val)

        ident = sql.Identifier(col)
        if op == "is":
            clauses.append(sql.SQL("{} is null").format(ident))
        elif op == "in":
            clauses.append(sql.SQL("{} = any(%s)").format(ident))
            params.append(list(v))
        else:
            clauses.append(sql.SQL("{} " + op + " %s").format(ident))
            params.append(v)
    return sql.SQL(" where ") + sql.SQL(" and ").join(clauses), params


# ── CRUD ────────────────────────────────────────────────────────

def select(table: str, *, filters: dict[str, Any] | None = None,
           columns: str = "*", order: str | None = None,
           limit: int | None = None) -> list[dict]:
    where, params = _where(filters)
    stmt = (sql.SQL("select {} from {}").format(
                sql.SQL(columns), sql.Identifier(table)) + where)
    if order:
        col, _, direction = order.partition(" ")
        stmt += sql.SQL(" order by {} {}").format(
            sql.Identifier(col),
            sql.SQL("desc" if direction.lower().startswith("desc") else "asc"))
    if limit:
        stmt += sql.SQL(" limit {}").format(sql.Literal(int(limit)))
    return query(stmt, params)


def select_one(table: str, **kw) -> dict | None:
    rows = select(table, limit=1, **kw)
    return rows[0] if rows else None


def insert(table: str, row: dict) -> dict:
    cols = list(row)
    stmt = sql.SQL("insert into {} ({}) values ({}) returning *").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, cols)),
        sql.SQL(", ").join(sql.Placeholder() * len(cols)),
    )
    rows = query(stmt, [row[c] for c in cols])
    return rows[0] if rows else {}


def update(table: str, filters: dict[str, Any], patch: dict) -> list[dict]:
    if not filters:
        raise DBError("update() without filters would rewrite every row")
    if not patch:
        return []
    where, wparams = _where(filters)
    assignments = sql.SQL(", ").join(
        sql.SQL("{} = %s").format(sql.Identifier(c)) for c in patch)
    stmt = (sql.SQL("update {} set ").format(sql.Identifier(table))
            + assignments + where + sql.SQL(" returning *"))
    return query(stmt, list(patch.values()) + wparams)


def upsert(table: str, row: dict, conflict: str | list[str]) -> dict:
    keys = [conflict] if isinstance(conflict, str) else list(conflict)
    cols = list(row)
    updates = [c for c in cols if c not in keys]
    stmt = sql.SQL(
        "insert into {} ({}) values ({}) on conflict ({}) do update set {} returning *"
    ).format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, cols)),
        sql.SQL(", ").join(sql.Placeholder() * len(cols)),
        sql.SQL(", ").join(map(sql.Identifier, keys)),
        sql.SQL(", ").join(
            sql.SQL("{0} = excluded.{0}").format(sql.Identifier(c)) for c in updates)
        if updates else sql.SQL("{0} = excluded.{0}").format(sql.Identifier(keys[0])),
    )
    rows = query(stmt, [row[c] for c in cols])
    return rows[0] if rows else {}


def delete(table: str, filters: dict[str, Any]) -> list[dict]:
    if not filters:
        raise DBError("delete() without filters would empty the table")
    where, params = _where(filters)
    stmt = (sql.SQL("delete from {}").format(sql.Identifier(table))
            + where + sql.SQL(" returning *"))
    return query(stmt, params)


def count(table: str, filters: dict[str, Any] | None = None) -> int:
    where, params = _where(filters)
    stmt = sql.SQL("select count(*) as n from {}").format(
        sql.Identifier(table)) + where
    rows = query(stmt, params)
    return int(rows[0]["n"]) if rows else 0


# ── Spend ledger ────────────────────────────────────────────────

def month_spend_usd() -> float:
    rows = query("select spent_usd from desk.usage_this_month")
    return float(rows[0]["spent_usd"]) if rows else 0.0


def under_cap() -> tuple[bool, float, float]:
    """(allowed, spent, cap). The runner refuses to call the model when
    this returns False — a budget that is not enforced is not a budget."""
    spent = month_spend_usd()
    return spent < config.MONTHLY_CAP_USD, spent, config.MONTHLY_CAP_USD


def ping() -> str:
    return query("select version() as v")[0]["v"].split(" on ")[0]
