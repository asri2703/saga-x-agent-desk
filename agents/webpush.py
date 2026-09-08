"""
Saga X Agent Desk — web push
============================
Sends notifications to installed PWAs, alongside Telegram.

Why both: Telegram is where Abang already is and needs no install, but
it is a separate app. Web push lands on the desk icon itself, which is
what he asked for when he said he would install this as an app. Neither
replaces the other, and a notification is only marked delivered once at
least one channel took it.

iOS specifics, which are the awkward ones:
  * the PWA must be added to the Home Screen — a Safari tab cannot
    subscribe, no matter how many times permission is requested
  * HTTPS with a real certificate is required; the desk has one now
  * permission must be requested from a user gesture, never on load

A subscription that returns 404 or 410 is gone for good — the browser
revoked it. Those get deleted rather than retried, or the queue fills
with sends that can never succeed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from . import config, db

MAX_FAILURES = 5


def configured() -> bool:
    return bool(config.get("VAPID_PRIVATE_KEY") and config.get("VAPID_PUBLIC_KEY"))


def public_key() -> str:
    """Handed to the browser so it can subscribe. Public by design."""
    return config.get("VAPID_PUBLIC_KEY", "")


def subscribe(subscription: dict, user_agent: str = "", label: str = "") -> dict:
    """Store a browser's subscription. Idempotent on the endpoint, so
    re-subscribing from the same browser updates rather than duplicates."""
    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys") or {}
    if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
        return {"ok": False, "error": "subscription missing endpoint or keys"}

    row = db.upsert("push_subscriptions", {
        "endpoint": endpoint,
        "p256dh": keys["p256dh"],
        "auth": keys["auth"],
        "user_agent": (user_agent or "")[:300] or None,
        "label": label or None,
        "failures": 0,
        "last_error": None,
    }, conflict="endpoint")
    return {"ok": True, "id": str(row.get("id", "")), "note": "subscribed"}


def unsubscribe(endpoint: str) -> dict:
    gone = db.delete("push_subscriptions", {"endpoint": endpoint})
    return {"ok": True, "removed": len(gone)}


def _drop(sub: dict, reason: str) -> None:
    db.delete("push_subscriptions", {"id": sub["id"]})


def send(title: str, body: str, url: str = "/", tag: str = "") -> dict:
    """Push to every subscribed browser. Returns counts, never raises —
    a failure here must not cost the notification its Telegram delivery."""
    if not configured():
        return {"sent": 0, "failed": 0, "note": "VAPID keys not set"}
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return {"sent": 0, "failed": 0, "note": "pywebpush not installed"}

    subs = db.select("push_subscriptions")
    if not subs:
        return {"sent": 0, "failed": 0, "note": "no subscribers"}

    payload = json.dumps({"title": title, "body": body,
                          "url": url, "tag": tag or "sagax"})
    claims = {"sub": config.get("VAPID_SUBJECT", "mailto:admin@sagaxventures.com")}
    sent = failed = dropped = 0

    for s in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": s["endpoint"],
                    "keys": {"p256dh": s["p256dh"], "auth": s["auth"]},
                },
                data=payload,
                vapid_private_key=config.get("VAPID_PRIVATE_KEY"),
                vapid_claims=dict(claims),
                ttl=86400,
            )
            db.update("push_subscriptions", {"id": s["id"]}, {
                "last_sent_at": datetime.now(timezone.utc),
                "failures": 0, "last_error": None})
            sent += 1
        except WebPushException as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            # 404/410: the browser revoked it. Retrying is pointless and
            # the row would otherwise fail forever.
            if code in (404, 410):
                _drop(s, f"revoked ({code})")
                dropped += 1
                continue
            n = int(s.get("failures") or 0) + 1
            if n >= MAX_FAILURES:
                _drop(s, "too many failures")
                dropped += 1
            else:
                db.update("push_subscriptions", {"id": s["id"]},
                          {"failures": n, "last_error": str(e)[:300]})
            failed += 1
        except Exception as e:
            failed += 1
            try:
                db.update("push_subscriptions", {"id": s["id"]},
                          {"last_error": str(e)[:300]})
            except Exception:
                pass

    return {"sent": sent, "failed": failed, "dropped": dropped,
            "subscribers": len(subs)}


def subscribers() -> list[dict]:
    rows = db.select("push_subscriptions",
                     columns="id,label,user_agent,created_at,last_sent_at,failures",
                     order="created_at desc")
    return [{k: (v.isoformat() if hasattr(v, "isoformat") else v)
             for k, v in r.items()} for r in rows]
