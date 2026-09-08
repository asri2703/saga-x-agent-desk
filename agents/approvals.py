"""
Saga X Agent Desk — executing approvals
=======================================
The agent queued an action. Abang approved it. This is what actually
performs it.

The rule the whole model rests on: **the payload is replayed as
stored**. The agent does not get to reinterpret the instruction after
approval, and nothing outside the stored payload influences what runs.
If the payload is wrong, the fix is to reject it and ask again — not
to let an executor "improve" it.

Anything with no registered executor is refused rather than guessed at.
An approval that silently does nothing is worse than one that errors,
because Abang will believe it happened.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

from . import db


class ApprovalError(RuntimeError):
    pass


def _payload(row: dict) -> dict:
    p = row.get("payload")
    if isinstance(p, str):
        try:
            return json.loads(p)
        except json.JSONDecodeError:
            return {}
    return p or {}


def _next_invoice_number() -> str:
    year = datetime.now(timezone.utc).year
    rows = db.query(
        "select number from desk.invoices where number like %s "
        "order by number desc limit 1", [f"INV-{year}-%"])
    if rows:
        try:
            return f"INV-{year}-{int(rows[0]['number'].rsplit('-', 1)[1]) + 1:03d}"
        except (ValueError, IndexError):
            pass
    return f"INV-{year}-001"


# ── Executors ───────────────────────────────────────────────────

def _exec_create_invoice(approval: dict, payload: dict) -> dict:
    lines = payload.get("lines") or []
    if not lines:
        raise ApprovalError("payload has no line items")

    client_id = payload.get("client_id") or approval.get("client_id")
    business = payload.get("business_id") or payload.get("business") or "agency"

    subtotal = Decimal("0")
    for ln in lines:
        qty = Decimal(str(ln.get("quantity") or ln.get("qty") or 1))
        price = Decimal(str(ln.get("unit_price") or ln.get("amount") or 0))
        subtotal += qty * price

    tax_rate = Decimal(str(payload.get("tax_rate") or 6))
    tax_enabled = bool(payload.get("tax_enabled") or payload.get("tax"))
    tax_amount = (subtotal * tax_rate / 100) if tax_enabled else Decimal("0")

    invoice = db.insert("invoices", {
        "business_id": business,
        "client_id": client_id,
        "project_id": payload.get("project_id"),
        "booking_id": payload.get("booking_id"),
        "subscription_id": payload.get("subscription_id"),
        "number": payload.get("number") or _next_invoice_number(),
        "status": "draft",
        "due_on": payload.get("due_on"),
        "currency": payload.get("currency") or "MYR",
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_enabled": tax_enabled,
        "tax_amount": tax_amount,
        "total": subtotal + tax_amount,
        "notes": payload.get("notes"),
    })

    for i, ln in enumerate(lines):
        db.insert("invoice_lines", {
            "invoice_id": invoice["id"],
            "service_id": ln.get("service_id"),
            "description": ln.get("description") or "Item",
            "qty": Decimal(str(ln.get("quantity") or ln.get("qty") or 1)),
            "unit_price": Decimal(str(ln.get("unit_price") or ln.get("amount") or 0)),
            "position": i,
        })

    return {"invoice_id": str(invoice["id"]), "number": invoice["number"],
            "total": float(invoice["total"]), "status": "draft",
            "note": "Created as a draft. Sending is a separate approval."}


def _exec_upsert_service(approval: dict, payload: dict) -> dict:
    if not payload.get("name") or payload.get("unit_price") is None:
        raise ApprovalError("service needs a name and a unit_price")
    row = db.insert("services", {
        "business_id": payload.get("business_id") or "agency",
        "name": payload["name"],
        "description": payload.get("description"),
        "kind": payload.get("kind") or "service",
        "unit_price": Decimal(str(payload["unit_price"])),
        "currency": payload.get("currency") or "MYR",
        "unit": payload.get("unit") or "per_project",
        "billing_period": payload.get("billing_period"),
    })
    return {"service_id": str(row["id"]), "name": row["name"],
            "unit_price": float(row["unit_price"])}


def _exec_record_payment(approval: dict, payload: dict) -> dict:
    invoice_id = payload.get("invoice_id")
    amount = payload.get("amount")
    if not invoice_id or amount is None:
        raise ApprovalError("payment needs invoice_id and amount")
    inv = db.select_one("invoices", filters={"id": invoice_id})
    if not inv:
        raise ApprovalError("no invoice with that id")
    paid = Decimal(str(inv["amount_paid"] or 0)) + Decimal(str(amount))
    total = Decimal(str(inv["total"] or 0))
    status = "paid" if paid >= total > 0 else "partial"
    db.update("invoices", {"id": invoice_id}, {
        "amount_paid": paid, "status": status,
        "paid_at": datetime.now(timezone.utc) if status == "paid" else None,
    })
    return {"invoice": inv["number"], "amount_paid": float(paid),
            "status": status}


EXECUTORS: dict[str, Callable[[dict, dict], dict]] = {
    "create_invoice": _exec_create_invoice,
    "create_service": _exec_upsert_service,
    "update_price": _exec_upsert_service,
    "record_payment": _exec_record_payment,
}


# ── Public API ──────────────────────────────────────────────────

def pending() -> list[dict]:
    return db.select("approvals_pending")


def approve(approval_id: str, via: str = "dashboard") -> dict:
    row = db.select_one("approvals", filters={"id": approval_id})
    if not row:
        raise ApprovalError("no approval with that id")
    if row["status"] != "pending":
        raise ApprovalError(f"already {row['status']}")

    expires = row.get("expires_at")
    if expires and expires < datetime.now(timezone.utc):
        db.update("approvals", {"id": approval_id},
                  {"status": "expired", "decided_at": datetime.now(timezone.utc)})
        raise ApprovalError("this approval expired; ask the agent again")

    executor = EXECUTORS.get(row["action_type"])
    if not executor:
        # Refuse rather than mark it done. A silent no-op would leave
        # Abang believing an invoice exists when it does not.
        raise ApprovalError(
            f"no executor for '{row['action_type']}' — this action cannot be "
            f"carried out automatically yet")

    db.update("approvals", {"id": approval_id}, {
        "status": "approved", "decided_at": datetime.now(timezone.utc),
        "decided_via": via,
    })

    try:
        result = executor(row, _payload(row))
    except Exception as e:
        db.update("approvals", {"id": approval_id},
                  {"status": "failed", "error": str(e)[:400]})
        raise ApprovalError(str(e)) from None

    db.update("approvals", {"id": approval_id}, {
        "status": "executed", "executed_at": datetime.now(timezone.utc),
        "result": json.dumps(result, default=str),
    })

    if row.get("run_id"):
        db.update("agent_runs", {"id": row["run_id"]}, {"status": "done"})

    return {"ok": True, "approval_id": approval_id, "result": result}


def reject(approval_id: str, via: str = "dashboard", reason: str = "") -> dict:
    row = db.select_one("approvals", filters={"id": approval_id})
    if not row:
        raise ApprovalError("no approval with that id")
    if row["status"] != "pending":
        raise ApprovalError(f"already {row['status']}")
    db.update("approvals", {"id": approval_id}, {
        "status": "rejected", "decided_at": datetime.now(timezone.utc),
        "decided_via": via, "error": reason or None,
    })
    if row.get("run_id"):
        db.update("agent_runs", {"id": row["run_id"]}, {"status": "cancelled"})
    return {"ok": True, "approval_id": approval_id, "status": "rejected"}


def expire_stale() -> int:
    rows = db.query("select desk.expire_stale_approvals() as n")
    return int(rows[0]["n"]) if rows else 0
