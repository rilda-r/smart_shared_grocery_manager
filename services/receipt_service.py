"""
services/receipt_service.py
===========================
Backend service for receipts, items, assignments, and payments.
Uses the PostgreSQL atomic RPC function `confirm_receipt_atomic` to guarantee
that receipt records, line item assignments, grocery item status updates,
and payment debts are created in a single, all-or-nothing transaction.
"""

import json
from decimal import Decimal
from typing import Dict, List, Any, Optional

from database.connection import execute, query_all, query_one, get_cursor


def confirm_receipt_transaction(
    room_id: int,
    uploaded_by: int,
    store: Optional[str],
    receipt_date: Optional[str],
    subtotal: Decimal,
    tax: Decimal,
    discount: Decimal,
    other_charges: Decimal,
    total: Decimal,
    image_path: Optional[str],
    items: List[Dict[str, Any]],
    payments: List[Dict[str, Any]],
    purchased_grocery_ids: List[int],
) -> Dict[str, Any]:
    """
    Execute the atomic Postgres RPC `confirm_receipt_atomic`.
    """
    # Prepare serializable items payload
    serializable_items = []
    for it in items:
        assignments = []
        for a in it.get("assignments", []):
            assignments.append({
                "user_id": int(a["user_id"]),
                "quantity": float(a["quantity"]),
                "amount": float(a["amount"]),
            })
        
        serializable_items.append({
            "name": str(it["name"]),
            "quantity": float(it["quantity"]),
            "unit_price": float(it["unit_price"]),
            "line_total": float(it["line_total"]),
            "matched_grocery_item_id": it.get("matched_grocery_item_id"),
            "is_extra": bool(it.get("is_extra", False)),
            "assignments": assignments,
        })

    serializable_payments = []
    for p in payments:
        serializable_payments.append({
            "payer_user_id": int(p["payer_user_id"]),
            "payee_user_id": int(p["payee_user_id"]),
            "amount": float(p["amount"]),
        })

    payload = {
        "receipt": {
            "room_id": int(room_id),
            "uploaded_by": int(uploaded_by),
            "store": store or None,
            "receipt_date": str(receipt_date) if receipt_date else None,
            "subtotal": float(subtotal),
            "tax": float(tax),
            "discount": float(discount),
            "other_charges": float(other_charges),
            "total": float(total),
            "image_path": image_path,
        },
        "items": serializable_items,
        "payments": serializable_payments,
        "purchased_grocery_ids": [int(gid) for gid in purchased_grocery_ids if gid],
    }

    payload_json = json.dumps(payload)

    with get_cursor() as cur:
        cur.execute("SELECT confirm_receipt_atomic(%s::jsonb) AS result", (payload_json,))
        row = cur.fetchone()

    if row and row.get("result"):
        res = row["result"]
        if isinstance(res, str):
            res = json.loads(res)
        return res

    return {"success": True, "message": "Receipt confirmed."}


def get_room_receipts(room_id: int) -> List[Dict[str, Any]]:
    """Fetch all receipts for a given room."""
    return query_all(
        """
        SELECT r.*, u.username AS uploader_username
        FROM receipts r
        JOIN users u ON u.id = r.uploaded_by
        WHERE r.room_id = %s
        ORDER BY r.created_at DESC, r.id DESC
        """,
        (int(room_id),)
    )


def get_receipt_details(receipt_id: int) -> Optional[Dict[str, Any]]:
    """Fetch receipt header, line items, and assignments."""
    receipt = query_one("SELECT * FROM receipts WHERE id = %s", (int(receipt_id),))
    if not receipt:
        return None

    items = query_all("SELECT * FROM receipt_items WHERE receipt_id = %s ORDER BY id ASC", (int(receipt_id),))
    for it in items:
        it["assignments"] = query_all(
            """
            SELECT a.*, u.username
            FROM receipt_item_assignments a
            JOIN users u ON u.id = a.user_id
            WHERE a.receipt_item_id = %s
            ORDER BY a.id ASC
            """,
            (it["id"],)
        )
    receipt["items"] = items
    return receipt
