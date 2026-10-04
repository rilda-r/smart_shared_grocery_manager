"""services/bill_service.py - bills, bill items, item matching and manual assignment."""

import re
from decimal import ROUND_HALF_UP, Decimal
from difflib import SequenceMatcher

from database.connection import execute, get_cursor, query_all, query_one
from models.bill import Bill
from models.bill_item import BillItem
from services import ocr_service
from services.room_service import get_member_role, require_room_member
from utils.helpers import (
    MONEY_QUANT,
    ServiceError,
    service_call,
    success_response,
    utcnow,
)
from utils.validators import (
    sanitize_file_name,
    validate_amount,
    validate_bill_file,
    validate_bill_quantity,
    validate_id,
    validate_item_name,
)

MATCH_THRESHOLD = 0.85      # confident automatic match
CANDIDATE_THRESHOLD = 0.60  # worth showing to the user as a suggestion
AMBIGUITY_MARGIN = 0.05     # runner-up this close => ambiguous


# ---------------------------------------------------------------------------
# Name matching (pure, unit-testable)
# ---------------------------------------------------------------------------
def _normalize_name(name: str) -> str:
    tokens = re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).split()
    return " ".join(t[:-1] if len(t) > 3 and t.endswith("s") else t for t in tokens)


def name_similarity(a: str, b: str) -> float:
    na, nb = _normalize_name(a), _normalize_name(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = set(na.split()), set(nb.split())
    jaccard = len(ta & tb) / len(ta | tb)
    contained = 0.88 if (ta <= tb or tb <= ta) else 0.0
    return max(SequenceMatcher(None, na, nb).ratio(), jaccard, contained)


def compute_item_matches(bill_items: list, grocery_items: list) -> dict:
    """Decide matches without touching the database.

    Returns ``{"matched": [...], "ambiguous": [...], "unmatched": [...]}``.
    Ambiguous items are NEVER auto-assigned.
    """
    matched, ambiguous, unmatched = [], [], []
    pool = [g for g in grocery_items if g["status"] != "unavailable"]
    for item in bill_items:
        if item.get("assigned_user_id") is not None:
            continue  # already decided (manually or earlier)
        scored = sorted(
            (
                {
                    "grocery_item_id": g["id"],
                    "user_id": g["user_id"],
                    "item_name": g["item_name"],
                    "score": round(name_similarity(item["item_name"], g["item_name"]), 2),
                }
                for g in pool
            ),
            key=lambda c: (-c["score"], c["grocery_item_id"]),
        )
        candidates = [c for c in scored if c["score"] >= CANDIDATE_THRESHOLD][:5]
        if not candidates:
            unmatched.append({"bill_item_id": item["id"], "item_name": item["item_name"]})
            continue
        top = candidates[0]
        contenders = [c for c in candidates if c["score"] >= top["score"] - AMBIGUITY_MARGIN]
        owners = {c["user_id"] for c in contenders}
        if top["score"] >= MATCH_THRESHOLD and len(owners) == 1:
            matched.append(
                {
                    "bill_item_id": item["id"],
                    "matched_grocery_item_id": top["grocery_item_id"],
                    "assigned_user_id": top["user_id"],
                    "score": top["score"],
                }
            )
        else:
            ambiguous.append(
                {
                    "bill_item_id": item["id"],
                    "item_name": item["item_name"],
                    "candidates": candidates,
                }
            )
    return {"matched": matched, "ambiguous": ambiguous, "unmatched": unmatched}


# ---------------------------------------------------------------------------
# Internal helpers (also used by expense_split_service / payment_service)
# ---------------------------------------------------------------------------
def load_bill_for_member(bill_id, user_id, cursor, for_update=False) -> dict:
    validate_id(bill_id, "bill id")
    validate_id(user_id, "user id")
    sql = "SELECT * FROM bills WHERE id = %s" + (" FOR UPDATE" if for_update else "")
    bill = query_one(sql, (bill_id,), cursor)
    if bill is None or get_member_role(bill["room_id"], user_id, cursor) is None:
        raise ServiceError("Bill not found.", "bill_not_found")
    return bill


def require_bill_manager(bill: dict, user_id, cursor) -> None:
    """Uploader or room creator only."""
    if bill["uploaded_by"] != user_id and get_member_role(bill["room_id"], user_id, cursor) != "creator":
        raise ServiceError(
            "Only the person who uploaded the bill or the room creator can do this.",
            "not_authorized",
        )


def bill_is_locked(bill_id: int, cursor) -> bool:
    row = query_one("SELECT COUNT(*) AS c FROM payments WHERE bill_id = %s", (bill_id,), cursor)
    return row["c"] > 0


def get_bill_items_rows(bill_id: int, cursor=None) -> list:
    return query_all("SELECT * FROM bill_items WHERE bill_id = %s ORDER BY id", (bill_id,), cursor)


def _bill_payload(bill_row: dict, cursor=None) -> dict:
    data = Bill.from_row(bill_row).to_dict()
    data["items"] = [BillItem.from_row(r).to_dict() for r in get_bill_items_rows(bill_row["id"], cursor)]
    return data


def _normalize_items(items, room_id: int, cursor) -> list:
    if not isinstance(items, (list, tuple)) or not items:
        raise ServiceError("A bill needs at least one item.", "invalid_bill_item")
    clean = []
    for index, raw in enumerate(items, start=1):
        if not isinstance(raw, dict):
            raise ServiceError(f"Bill item {index} is invalid.", "invalid_bill_item")
        try:
            name = validate_item_name(raw.get("item_name"))
            quantity = validate_bill_quantity(raw.get("quantity", 1))
            unit_raw, total_raw = raw.get("unit_price"), raw.get("total_price")
            if unit_raw is None and total_raw is None:
                raise ServiceError("Price is required.", "invalid_bill_item")
            if total_raw is not None:
                total = validate_amount(total_raw, "Total price", allow_zero=True)
                unit = (
                    validate_amount(unit_raw, "Unit price", allow_zero=True)
                    if unit_raw is not None
                    else (total / quantity).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
                )
            else:
                unit = validate_amount(unit_raw, "Unit price", allow_zero=True)
                total = (unit * quantity).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        except ServiceError as exc:
            raise ServiceError(f"Bill item {index}: {exc.message}", "invalid_bill_item")
        matched = raw.get("matched_grocery_item_id")
        if matched is not None:
            validate_id(matched, "grocery item id")
            ok = query_one(
                "SELECT 1 AS ok FROM grocery_items WHERE id = %s AND room_id = %s",
                (matched, room_id),
                cursor,
            )
            if ok is None:
                raise ServiceError(f"Bill item {index}: unknown grocery item.", "invalid_bill_item")
        assigned = raw.get("assigned_user_id")
        if assigned is not None:
            validate_id(assigned, "user id")
            if get_member_role(room_id, assigned, cursor) is None:
                raise ServiceError(f"Bill item {index}: assignee is not a room member.", "invalid_bill_item")
        item_id = raw.get("id")
        if item_id is not None:
            validate_id(item_id, "bill item id")
        clean.append(
            {
                "id": item_id,
                "item_name": name,
                "quantity": quantity,
                "unit_price": unit,
                "total_price": total,
                "matched_grocery_item_id": matched,
                "assigned_user_id": assigned,
            }
        )
    return clean


def _write_items(bill_id: int, items: list, cursor) -> None:
    existing = {r["id"] for r in query_all("SELECT id FROM bill_items WHERE bill_id = %s", (bill_id,), cursor)}
    keep = set()
    for item in items:
        values = (
            item["item_name"], item["quantity"], item["unit_price"], item["total_price"],
            item["matched_grocery_item_id"], item["assigned_user_id"],
        )
        if item["id"] is not None:
            if item["id"] not in existing:
                raise ServiceError("A bill item does not belong to this bill.", "invalid_bill_item")
            execute(
                "UPDATE bill_items SET item_name = %s, quantity = %s, unit_price = %s, "
                "total_price = %s, matched_grocery_item_id = %s, assigned_user_id = %s "
                "WHERE id = %s AND bill_id = %s",
                (*values, item["id"], bill_id),
                cursor,
            )
            keep.add(item["id"])
        else:
            keep.add(
                execute(
                    "INSERT INTO bill_items (bill_id, item_name, quantity, unit_price, total_price, "
                    "matched_grocery_item_id, assigned_user_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (bill_id, *values),
                    cursor,
                )
            )
    for stale in existing - keep:
        execute("DELETE FROM bill_items WHERE id = %s AND bill_id = %s", (stale, bill_id), cursor)


def _items_total(items: list) -> Decimal:
    return sum((i["total_price"] for i in items), Decimal("0.00")).quantize(MONEY_QUANT)


def _run_matching(bill_id: int, room_id: int, cursor) -> dict:
    bill_items = get_bill_items_rows(bill_id, cursor)
    groceries = query_all("SELECT * FROM grocery_items WHERE room_id = %s", (room_id,), cursor)
    result = compute_item_matches(bill_items, groceries)
    for m in result["matched"]:
        execute(
            "UPDATE bill_items SET matched_grocery_item_id = %s, assigned_user_id = %s "
            "WHERE id = %s AND bill_id = %s AND assigned_user_id IS NULL",
            (m["matched_grocery_item_id"], m["assigned_user_id"], m["bill_item_id"], bill_id),
            cursor,
        )
    return result


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------
@service_call
def create_bill(user_id, room_id, file_name=None, file_bytes=None, items=None,
                total_amount=None, ocr_provider=None):
    """Create a bill from an uploaded file (OCR) or from manually entered ``items``.

    OCR failure is NOT an error: the bill is created with ``ocr_status == "failed"``
    and ``manual_entry_required == True`` so the caller can use ``update_bill_items``.
    """
    explicit_total = validate_amount(total_amount, "Total amount") if total_amount is not None else None

    if items is not None:  # ------------------------------ manual entry
        with get_cursor() as cur:
            require_room_member(room_id, user_id, cur)
            clean = _normalize_items(items, room_id, cur)
            name = sanitize_file_name(file_name) or "manual-entry"
            bill_id = execute(
                "INSERT INTO bills (room_id, uploaded_by, file_name, ocr_status, total_amount, created_at) "
                "VALUES (%s, %s, %s, 'completed', %s, %s)",
                (room_id, user_id, name, explicit_total or _items_total(clean), utcnow()),
                cur,
            )
            _write_items(bill_id, clean, cur)
            matching = _run_matching(bill_id, room_id, cur)
            payload = _bill_payload(query_one("SELECT * FROM bills WHERE id = %s", (bill_id,), cur), cur)
        payload.update(manual_entry_required=False, matching=matching)
        return success_response(payload, "Bill created.")

    if file_bytes is None:
        raise ServiceError("Upload a bill file or enter items manually.", "invalid_input")

    safe_name = validate_bill_file(file_name, file_bytes)
    with get_cursor() as cur:
        require_room_member(room_id, user_id, cur)
        bill_id = execute(
            "INSERT INTO bills (room_id, uploaded_by, file_name, ocr_status, total_amount, created_at) "
            "VALUES (%s, %s, %s, 'processing', 0, %s)",
            (room_id, user_id, safe_name, utcnow()),
            cur,
        )

    result = ocr_service.process_bill(file_bytes, safe_name, ocr_provider)
    matching = {"matched": [], "ambiguous": [], "unmatched": []}
    with get_cursor() as cur:
        if result["success"]:
            clean = _normalize_items(result["data"]["items"], room_id, cur)
            total = explicit_total or result["data"]["total_amount"] or _items_total(clean)
            _write_items(bill_id, clean, cur)
            execute(
                "UPDATE bills SET ocr_status = 'completed', total_amount = %s WHERE id = %s",
                (total, bill_id),
                cur,
            )
            matching = _run_matching(bill_id, room_id, cur)
        else:
            execute("UPDATE bills SET ocr_status = 'failed' WHERE id = %s", (bill_id,), cur)
        payload = _bill_payload(query_one("SELECT * FROM bills WHERE id = %s", (bill_id,), cur), cur)
    payload.update(manual_entry_required=not result["success"], matching=matching)
    message = "Bill processed." if result["success"] else result["message"]
    return success_response(payload, message)


@service_call
def get_bill(user_id, bill_id):
    with get_cursor() as cur:
        bill = load_bill_for_member(bill_id, user_id, cur)
        return success_response(_bill_payload(bill, cur))


@service_call
def update_bill_items(user_id, bill_id, items, total_amount=None):
    """Replace the bill's items (rows carrying an ``id`` are updated, others inserted,
    omitted rows deleted). Locked once a split has been confirmed."""
    explicit_total = validate_amount(total_amount, "Total amount") if total_amount is not None else None
    with get_cursor() as cur:
        bill = load_bill_for_member(bill_id, user_id, cur, for_update=True)
        require_bill_manager(bill, user_id, cur)
        if bill_is_locked(bill_id, cur):
            raise ServiceError("This bill's split is already confirmed.", "bill_locked")
        clean = _normalize_items(items, bill["room_id"], cur)
        _write_items(bill_id, clean, cur)
        execute(
            "UPDATE bills SET total_amount = %s WHERE id = %s",
            (explicit_total or _items_total(clean), bill_id),
            cur,
        )
        matching = _run_matching(bill_id, bill["room_id"], cur)
        payload = _bill_payload(query_one("SELECT * FROM bills WHERE id = %s", (bill_id,), cur), cur)
    payload["matching"] = matching
    return success_response(payload, "Bill items updated.")


@service_call
def match_bill_items(user_id, bill_id):
    """(Re)run automatic matching for still-unassigned items."""
    with get_cursor() as cur:
        bill = load_bill_for_member(bill_id, user_id, cur, for_update=True)
        if bill_is_locked(bill_id, cur):
            raise ServiceError("This bill's split is already confirmed.", "bill_locked")
        result = _run_matching(bill_id, bill["room_id"], cur)
    return success_response(result)


@service_call
def assign_bill_item(user_id, bill_id, bill_item_id, assigned_user_id):
    """Manually assign (or clear with ``None``) a bill item's owner."""
    validate_id(bill_item_id, "bill item id")
    with get_cursor() as cur:
        bill = load_bill_for_member(bill_id, user_id, cur, for_update=True)
        if bill_is_locked(bill_id, cur):
            raise ServiceError("This bill's split is already confirmed.", "bill_locked")
        item = query_one(
            "SELECT * FROM bill_items WHERE id = %s AND bill_id = %s FOR UPDATE",
            (bill_item_id, bill_id),
            cur,
        )
        if item is None:
            raise ServiceError("Bill item not found.", "invalid_bill_item")
        if assigned_user_id is not None:
            validate_id(assigned_user_id, "user id")
            if get_member_role(bill["room_id"], assigned_user_id, cur) is None:
                raise ServiceError("The assignee is not a member of this room.", "invalid_bill_item")
        execute(
            "UPDATE bill_items SET assigned_user_id = %s WHERE id = %s",
            (assigned_user_id, bill_item_id),
            cur,
        )
        row = query_one("SELECT * FROM bill_items WHERE id = %s", (bill_item_id,), cur)
    return success_response(BillItem.from_row(row).to_dict(), "Item assigned.")
