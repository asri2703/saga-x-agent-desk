"""
Saga X Agent Desk — notification sender
=======================================
Drains desk.notifications to Telegram.

Deliberately separate from monitors.py. Alisya queues; this sends. That
split means a Telegram outage cannot cost us a monitoring result, and a
notification can be retried without re-running the check.

The bot token lives on the VPS, where server.py already uses it for
tg_send(). Nothing needs to hand the funnel bot's token anywhere new —
locally this simply no-ops and the queue waits.

TG_ALLOWED_CHAT_IDS is the recipient list. It is also the allowlist for
inbound /desk_* commands: the webhook secret alone is a weak control
for a bot that also runs a sales funnel.

Run from cron, a few minutes after the monitor sweep:
    python -m agents.notify
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

from . import config, db

API = "https://api.telegram.org/bot{token}/sendMessage"
BATCH = 20


def send_telegram(chat_id: str, text: str) -> tuple[bool, str]:
    if not config.TG_BOT_TOKEN:
        return False, "TG_BOT_TOKEN not set"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(
        API.format(token=config.TG_BOT_TOKEN),
        data=payload,
        headers={"Content-Type": "application/json",
                 "User-Agent": "SagaXDesk/2.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = json.loads(r.read())
        return bool(body.get("ok")), "" if body.get("ok") else str(body)[:200]
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read()[:150].decode('utf-8', 'replace')}"
    except Exception as e:
        return False, str(e)[:200]


def drain() -> dict:
    """Send everything pending. Failures stay pending and are retried on
    the next run rather than being dropped or marked delivered."""
    pending = db.select("notifications", filters={"delivered": False},
                        order="created_at asc", limit=BATCH)
    if not pending:
        return {"pending": 0, "sent": 0, "failed": 0}

    recipients = config.TG_ALLOWED_CHAT_IDS
    if not recipients:
        return {"pending": len(pending), "sent": 0, "failed": 0,
                "note": "TG_ALLOWED_CHAT_IDS not set — nothing to send to"}
    if not config.TG_BOT_TOKEN:
        return {"pending": len(pending), "sent": 0, "failed": 0,
                "note": "TG_BOT_TOKEN not set — queue is waiting"}

    sent = failed = 0
    for n in pending:
        title = n.get("title") or "Saga X Desk"
        text = f"{title}\n\n{n.get('body') or ''}".strip()

        results = [send_telegram(c, text) for c in recipients]

        # Web push runs alongside, not instead. It must never be able to
        # cost a notification its Telegram delivery, hence the catch.
        try:
            from . import webpush
            push = webpush.send(title, (n.get("body") or "")[:300], url="/")
        except Exception as e:
            push = {"sent": 0, "error": str(e)[:120]}

        if any(ok for ok, _ in results) or push.get("sent"):
            db.update("notifications", {"id": n["id"]}, {
                "delivered": True,
                "sent_at": datetime.now(timezone.utc),
                "error": None,
            })
            sent += 1
        else:
            # Record why, leave it pending for the next sweep.
            db.update("notifications", {"id": n["id"]},
                      {"error": "; ".join(e for _, e in results)[:400]})
            failed += 1

    return {"pending": len(pending), "sent": sent, "failed": failed}


if __name__ == "__main__":
    print(drain())
