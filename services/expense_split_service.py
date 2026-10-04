"""services/expense_split_service.py - member-wise and equal bill splitting.

Money is handled in integer cents with the largest-remainder method, so the
shares ALWAYS add up to the bill total exactly; the total itself is never
altered to make the numbers fit.

Payment direction: every member (other than the bill's uploader, who paid the
shop) owes their share to the uploader -> ``payer_user_id`` = debtor,
``payee_user_id`` = bill uploader.
"""

from collections import defaultdict
from decimal import Decimal

from database.connection import execute, get_cursor, query_all, query_one
from models.payment import Payment
from services.bill_service import (
    get_bill_items_rows,
    load_bill_for_member,
    require_bill_manager,
)
from services.room_service import get_member_role
from utils.helpers import MONEY_QUANT, ServiceError, service_call, success_response, utcnow
from utils.validators import validate_id

SPLIT_MEMBER_WISE = "member_wise"
SPLIT_EQUAL = "equal"


def _to_cents(amount: Decimal) -> int:
    return int((Decimal(amount) * 100).to_integral_value())


def _from_cents(cents: int) -> Decimal:
    return (Decimal(cents) / 100).quantize(MONEY_QUANT)


def allocate_proportionally(total: Decimal, weights: dict) -> dict:
    """Split ``total`` across keys in proportion to ``weights`` (largest remainder).

    Guarantees ``sum(result.values()) == total``. Zero/negative weights get nothing;
    leftover cents go to the largest fractional remainders (ties: lowest key).
    """
    total_cents = _to_cents(total)
    w = {k: _to_cents(v) for k, v in weights.items() if v > 0}
    weight_sum = sum(w.values())
    if total_cents <= 0 or weight_sum <= 0:
        raise ServiceError("There is nothing to split.", "invalid_bill_total")
    base, remainder = {}, {}
    for key, weight in w.items():
        base[key], remainder[key] = divmod(total_cents * weight, weight_sum)
    leftover = total_cents - sum(base.values())
    for key in sorted(remainder, key=lambda k: (-remainder[k], k))[:leftover]:
        base[key] += 1
    return {key: _from_cents(cents) for key, cents in base.items()}


def _shares_payload(bill: dict, split_type: str, shares: dict, subtotals=None) -> dict:
    ordered = sorted(shares.items())
    assert sum(s for _, s in ordered) == bill["total_amount"], "shares must reconcile"
    return {
        "bill_id": bill["id"],
        "split_type": split_type,
        "total_amount": bill["total_amount"],
        "paid_by": bill["uploaded_by"],
        "shares": [
            {
                "user_id": uid,
                "amount": amount,
                **({"items_subtotal": subtotals[uid]} if subtotals else {}),
            }
            for uid, amount in ordered
        ],
    }


def _require_splittable(bill: dict) -> None:
    if bill["total_amount"] <= 0:
        raise ServiceError("The bill total must be greater than zero.", "invalid_bill_total")


def _member_wise(bill: dict, cursor) -> dict:
    _require_splittable(bill)
    items = get_bill_items_rows(bill["id"], cursor)
    if not items:
        raise ServiceError("This bill has no items.", "no_items")
    unassigned = [i["id"] for i in items if i["assigned_user_id"] is None]
    if unassigned:
        raise ServiceError(
            "Some bill items are not assigned to a member yet.",
            "unassigned_items",
            {"unassigned_item_ids": unassigned},
        )
    subtotals = defaultdict(lambda: Decimal("0.00"))
    for item in items:
        subtotals[item["assigned_user_id"]] += item["total_price"]
    shares = allocate_proportionally(bill["total_amount"], subtotals)
    return _shares_payload(bill, SPLIT_MEMBER_WISE, shares, dict(subtotals))


def _equal(bill: dict, member_ids, cursor) -> dict:
    _require_splittable(bill)
    if member_ids is None:
        rows = query_all("SELECT user_id FROM room_members WHERE room_id = %s", (bill["room_id"],), cursor)
        member_ids = [r["user_id"] for r in rows]
    if not isinstance(member_ids, (list, tuple, set)) or not member_ids:
        raise ServiceError("Select at least one member to split with.", "invalid_input")
    unique = set()
    for member_id in member_ids:
        validate_id(member_id, "user id")
        if get_member_role(bill["room_id"], member_id, cursor) is None:
            raise ServiceError("Every member in the split must belong to this room.", "invalid_input")
        unique.add(member_id)
    shares = allocate_proportionally(bill["total_amount"], {m: Decimal(1) for m in unique})
    return _shares_payload(bill, SPLIT_EQUAL, shares)


@service_call
def calculate_member_shares(user_id, bill_id):
    """Preview: each member's share based on the items assigned to them."""
    with get_cursor() as cur:
        bill = load_bill_for_member(bill_id, user_id, cur)
        return success_response(_member_wise(bill, cur))


@service_call
def calculate_equal_split(user_id, bill_id, member_ids=None):
    """Preview: split the bill total equally (default: all room members)."""
    with get_cursor() as cur:
        bill = load_bill_for_member(bill_id, user_id, cur)
        return success_response(_equal(bill, member_ids, cur))


@service_call
def confirm_bill_split(user_id, bill_id, split_type=SPLIT_MEMBER_WISE, member_ids=None):
    """Recompute the split on the server, store it and (re)generate payment records.

    Shares are never taken from the caller. Only the uploader or room creator may
    confirm, and not once any payment of the bill has been reported/settled.
    """
    if split_type not in (SPLIT_MEMBER_WISE, SPLIT_EQUAL):
        raise ServiceError("split_type must be 'member_wise' or 'equal'.", "invalid_input")
    with get_cursor() as cur:
        bill = load_bill_for_member(bill_id, user_id, cur, for_update=True)
        require_bill_manager(bill, user_id, cur)
        existing = query_all("SELECT payment_status FROM payments WHERE bill_id = %s", (bill_id,), cur)
        if any(p["payment_status"] != "pending" for p in existing):
            raise ServiceError(
                "Payments for this bill have already been reported or settled.",
                "split_already_settled",
            )
        result = (
            _member_wise(bill, cur)
            if split_type == SPLIT_MEMBER_WISE
            else _equal(bill, member_ids, cur)
        )
        execute("DELETE FROM payments WHERE bill_id = %s AND payment_status = 'pending'", (bill_id,), cur)
        now = utcnow()
        for share in result["shares"]:
            if share["user_id"] == bill["uploaded_by"] or share["amount"] <= 0:
                continue
            execute(
                "INSERT INTO payments (room_id, bill_id, payer_user_id, payee_user_id, amount, "
                "payment_status, created_at) VALUES (%s, %s, %s, %s, %s, 'pending', %s)",
                (bill["room_id"], bill_id, share["user_id"], bill["uploaded_by"], share["amount"], now),
                cur,
            )
        rows = query_all("SELECT * FROM payments WHERE bill_id = %s ORDER BY id", (bill_id,), cur)
    result["payments"] = [Payment.from_row(r).to_dict() for r in rows]
    return success_response(result, "Split confirmed.")
