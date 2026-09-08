"""
Saga X Agent Desk — configuration
=================================
Loads .env with the standard library. No python-dotenv dependency;
the file format we use is simple enough not to need one.

Precedence: a real environment variable always beats .env. That way
systemd on the VPS stays authoritative in production, while .env is
the convenience for local work.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path | None = None) -> dict[str, str]:
    """Read KEY=VALUE lines from .env. Comments and blanks ignored.

    Trailing ` # comment` is stripped, which is how our .env is
    written. Values are not unquoted beyond surrounding quotes —
    we have no need for shell-style escaping.
    """
    path = path or (ROOT / ".env")
    found: dict[str, str] = {}
    if not path.is_file():
        return found
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        # Strip an inline comment, but not a '#' inside a quoted value.
        if not val.strip().startswith(("'", '"')):
            val = val.split("#")[0]
        val = val.strip().strip("'\"")
        if key:
            found[key] = val
    return found


_FILE_ENV = load_env()


def get(name: str, default: str = "") -> str:
    """Real environment first, then .env, then the default."""
    return os.environ.get(name) or _FILE_ENV.get(name) or default


def require(name: str) -> str:
    """For values with no safe default. Fails loudly at startup rather
    than mysteriously at the first request."""
    val = get(name)
    if not val:
        raise RuntimeError(
            f"{name} is not set. Add it to .env or the systemd unit. "
            f"See .env.example."
        )
    return val


# ── Supabase ────────────────────────────────────────────────────
SUPABASE_URL = get("SUPABASE_URL").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = get("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = get("SUPABASE_ANON_KEY")
SUPABASE_SCHEMA = get("SUPABASE_SCHEMA", "desk")

# ── OpenAI ──────────────────────────────────────────────────────
OPENAI_API_KEY = get("OPENAI_API_KEY")
OPENAI_ORG_ID = get("OPENAI_ORG_ID")
OPENAI_MODEL = get("OPENAI_MODEL", "gpt-5.6-sol")
OPENAI_REASONING_EFFORT = get("OPENAI_REASONING_EFFORT", "low")

# Hard ceiling. The runner refuses to call the API past this for the
# calendar month. A budget that is not enforced is not a budget.
try:
    MONTHLY_CAP_USD = float(get("MONTHLY_CAP_USD", "15"))
except ValueError:
    MONTHLY_CAP_USD = 15.0

# ── Telegram ────────────────────────────────────────────────────
# The same bot serves the Mastery Signal funnel. Treat with care.
TG_BOT_TOKEN = get("TG_BOT_TOKEN")
TG_WEBHOOK_SECRET = get("TG_WEBHOOK_SECRET")
TG_ALLOWED_CHAT_IDS = [
    c.strip() for c in get("TG_ALLOWED_CHAT_IDS").split(",") if c.strip()
]

# ── Server ──────────────────────────────────────────────────────
# 127.0.0.1 locally so the desk is not served to the whole WiFi.
# Production sets 0.0.0.0 explicitly via systemd, behind nginx.
HOST = get("HOST", "127.0.0.1")
PORT = int(get("PORT", "8080"))
AUTH_REQUIRED = get("AUTH_REQUIRED", "0") == "1"
POST_TOKEN = get("POST_TOKEN")

CORS_ALLOWED_ORIGINS = [
    o.strip() for o in get("CORS_ALLOWED_ORIGINS").split(",") if o.strip()
]

# Schedules are written in Abang's time, not UTC. "setiap hari 9 pagi"
# must mean 9am in Kuala Lumpur; computing in UTC would fire it at 5pm.
TIMEZONE = get("TIMEZONE", "Asia/Kuala_Lumpur")


def tzinfo():
    from zoneinfo import ZoneInfo
    try:
        return ZoneInfo(TIMEZONE)
    except Exception:
        from datetime import timezone as _tz
        return _tz.utc


# The five staff. "Hermes" is Putri's name on Telegram, not a sixth
# agent — hence @putrihermes_bot.
AGENTS = ("putri", "alisya", "julia", "farah", "delisha")

AGENT_ROLES = {
    "putri": ("Putri", "CEO"),
    "alisya": ("Alisya", "CTO"),
    "julia": ("Julia", "CFO"),
    "farah": ("Farah", "CMO"),
    "delisha": ("Delisha", "COO"),
}

VALID_STATES = ("idle", "thinking", "working", "done", "error", "offline")


def health() -> dict[str, bool]:
    """What is configured. Used by the preflight check so we can see
    what is missing without printing any secret."""
    return {
        "supabase_url": bool(SUPABASE_URL),
        "supabase_service_role_key": bool(SUPABASE_SERVICE_ROLE_KEY),
        "supabase_anon_key": bool(SUPABASE_ANON_KEY),
        "openai_api_key": bool(OPENAI_API_KEY),
        "telegram_bot_token": bool(TG_BOT_TOKEN),
        "telegram_allowlist": bool(TG_ALLOWED_CHAT_IDS),
    }
