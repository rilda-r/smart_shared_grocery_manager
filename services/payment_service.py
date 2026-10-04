"""services/payment_service.py - payment obligation tracking (no payment gateway).

* ``payer_user_id`` owes ``amount`` to ``payee_user_id``.
* The payer may ``report_payment`` ("I paid"); only the payee may
  ``settle_payment`` (confirms receipt). Settled rows are kept as history.
"""

from collections import defaultdict
from decimal import Decimal

from database.connection import execute, get_cursor, query_all, query_one
from models.payment import Payment
from services.room_service import require_room_member
from utils.helpers import MONEY_QUANT, ServiceError, service_call, success_response, utcnow
from utils.validators import validate_id
from config.settings import PAYMENT_STATUSES


def _load_payment(payment_id, user_id, cursor, for_update=False) -> dict:
    validate_id(payment_id, "payment id")
    validate_id(user_id, "user id")
    sql = "SELECT * FROM payments WHERE id = %s" + (" FOR UPDATE" if for_update else "")
    payment = query_one(sql, (payment_id,), cursor)
    member = payment and query_one(
        "SELECT 1 AS ok FROM room_members WHERE room_id = %s AND user_id = %s",
        (payment["room_id"], user_id),
        cursor,
    )
    if payment is None or member is None:
        raise ServiceError("Payment not found.", "payment_not_found")
    return payment


@service_call
def get_room_payments(user_id, room_id, status=None):
    require_room_member(room_id, user_id)
    sql = "SELECT * FROM payments WHERE room_id = %s"
    params = [room_id]
    if status is not None:
        if status not in PAYMENT_STATUSES:
            raise ServiceError("Invalid payment status.", "invalid_input")
        sql += " AND payment_status = %s"
        params.append(status)
    rows = query_all(sql + " ORDER BY created_at DESC, id DESC", tuple(params))
    return success_response([Payment.from_row(r).to_dict() for r in rows])


@service_call
def settle_payment(user_id, payment_id):
    """Payee confirms receipt. Rejects duplicates and non-payees."""
    with get_cursor() as cur:
        payment = _load_payment(payment_id, user_id, cur, for_update=True)
        if payment["payee_user_id"] != user_id:
            raise ServiceError("Only the person owed can settle this payment.", "not_authorized")
        if payment["payment_status"] == "settled":
            raise ServiceError("This payment has already been settled.", "duplicate_settlement")
        execute(
            "UPDATE payments SET payment_status = 'settled', settled_at = %s WHERE id = %s",
            (utcnow(), payment_id),
            cur,
        )
        row = query_one("SELECT * FROM payments WHERE id = %s", (payment_id,), cur)
    return success_response(Payment.from_row(row).to_dict(), "Payment settled.")


@service_call
def report_payment(user_id, payment_id):
    """Payer reports that they have paid (awaiting the payee's settlement)."""
    with get_cursor() as cur:
        payment = _load_payment(payment_id, user_id, cur, for_update=True)
        if payment["payer_user_id"] != user_id:
            raise ServiceError("Only the person who owes this payment can report it.", "not_authorized")
        if payment["payment_status"] == "settled":
            raise ServiceError("This payment has already been settled.", "duplicate_settlement")
        if payment["payment_status"] == "reported":
            raise ServiceError("This payment has already been reported.", "duplicate_report")
        execute(
            "UPDATE payments SET payment_status = 'reported', reported_at = %s WHERE id = %s",
            (utcnow(), payment_id),
            cur,
        )
        row = query_one("SELECT * FROM payments WHERE id = %s", (payment_id,), cur)
    return success_response(Payment.from_row(row).to_dict(), "Payment reported.")


@service_call
def recalculate_balances(user_id, room_id):
    """Net outstanding balance per member from unsettled payments.

    Positive = the member is owed money; negative = the member owes money.
    """
    with get_cursor() as cur:
        require_room_member(room_id, user_id, cur)
        members = query_all(
            "SELECT m.user_id, u.username FROM room_members m JOIN users u ON u.id = m.user_id "
            "WHERE m.room_id = %s ORDER BY m.joined_at, m.user_id",
            (room_id,),
            cur,
        )
        open_payments = query_all(
            "SELECT payer_user_id, payee_user_id, amount FROM payments "
            "WHERE room_id = %s AND payment_status <> 'settled'",
            (room_id,),
            cur,
        )
    balances = defaultdict(lambda: Decimal("0.00"))
    for p in open_payments:
        balances[p["payee_user_id"]] += p["amount"]
        balances[p["payer_user_id"]] -= p["amount"]
    return success_response(
        {
            "room_id": room_id,
            "outstanding_count": len(open_payments),
            "balances": [
                {
                    "user_id": m["user_id"],
                    "username": m["username"],
                    "balance": balances[m["user_id"]].quantize(MONEY_QUANT),
                }
                for m in members
            ],
        }
    )
