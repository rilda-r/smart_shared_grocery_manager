"""
services/receipt_split_service.py
=================================
Per-item cost allocation with exact-paisa reconciliation.

Per-receipt-row formula
-----------------------
  gross        = line_total
  item_disc    = item_discount
  coupon_share = coupon_discount * (gross - item_disc) / Σ(gross - item_disc)
  taxable      = gross - item_disc - coupon_share
  gst_amt      = taxable * gst_rate / 100
  cgst_amt     = sgst_amt = gst_amt / 2
  row_payable  = taxable + gst_amt

Then share other_charges and round_off across rows ∝ row_payable.
  final_row    = row_payable + row_other_share + row_roundoff_share

sum(final_row) must == net_payable ± 0.01; difference assigned to largest row.

If a row has multiple users, split final_row equally (or by quantity share).
"""

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any, Tuple, Optional

MONEY_ROUND = Decimal("0.01")
QTY_ROUND   = Decimal("0.001")


def _d(v, default="0.00") -> Decimal:
    """Safe Decimal coercion."""
    if isinstance(v, Decimal):
        return v
    try:
        return Decimal(str(v)).quantize(MONEY_ROUND, rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal(default)


def to_cents(val: Decimal) -> int:
    return int((Decimal(str(val)) * 100).to_integral_value(rounding=ROUND_HALF_UP))


def from_cents(cents: int) -> Decimal:
    return (Decimal(cents) / Decimal(100)).quantize(MONEY_ROUND)


def _split_proportionally(total: Decimal, weights: Dict[Any, Decimal]) -> Dict[Any, Decimal]:
    """Largest-remainder paisa-accurate proportional split."""
    total_cents = to_cents(total)
    if total_cents == 0 or not weights:
        return {k: Decimal("0.00") for k in weights}

    pos_weights = {k: max(0, to_cents(w)) for k, w in weights.items()}
    sum_w = sum(pos_weights.values())
    is_neg = total_cents < 0
    abs_c = abs(total_cents)

    if sum_w <= 0:
        n = len(weights)
        base_c = abs_c // n
        rem = abs_c % n
        res = {}
        for i, k in enumerate(sorted(weights.keys())):
            c = base_c + (1 if i < rem else 0)
            res[k] = from_cents(-c if is_neg else c)
        return res

    base = {}
    remainders = {}
    for k, wc in pos_weights.items():
        q = (abs_c * wc) // sum_w
        r = (abs_c * wc) % sum_w
        base[k] = q
        remainders[k] = r

    leftover = abs_c - sum(base.values())
    for k in sorted(pos_weights.keys(), key=lambda k: (-remainders[k], k))[:leftover]:
        base[k] += 1

    return {k: from_cents(-base[k] if is_neg else base[k]) for k in weights}


def _split_equally(total: Decimal, keys: List[Any]) -> Dict[Any, Decimal]:
    return _split_proportionally(total, {k: Decimal("1") for k in keys})


# ─────────────────────────────────────────────────────────────────────────────

def allocate_per_item(
    receipt_rows: List[Dict[str, Any]],
    coupon_discount: Decimal,
    other_charges: Decimal,
    round_off: Decimal,
    net_payable: Decimal,
) -> List[Dict[str, Any]]:
    """
    Per-item allocation returning one enriched dict per row:
      {name, quantity, gross, item_disc, coupon_share,
       taxable, gst_rate, gst_amt, cgst_amt, sgst_amt,
       row_payable, other_share, roundoff_share, final_row_amount}
    Guarantees sum(final_row_amount) == net_payable exactly.
    """
    rows = []
    for r in receipt_rows:
        gross     = _d(r.get("line_total", 0))
        item_disc = _d(r.get("item_discount", 0))
        gst_rate  = float(r.get("gst_rate", 0) or 0)
        rows.append({
            "name":      r.get("name", ""),
            "quantity":  r.get("quantity", Decimal("1")),
            "gross":     gross,
            "item_disc": item_disc,
            "gst_rate":  gst_rate,
            "_orig":     r,  # keep for user assignments
        })

    # ── coupon proportional share ─────────────────────────────────────────────
    net_after_item = [max(Decimal("0.00"), r["gross"] - r["item_disc"]) for r in rows]
    sum_net = sum(net_after_item) or Decimal("1")

    coupon_weights = {i: net_after_item[i] for i in range(len(rows))}
    coupon_shares  = _split_proportionally(coupon_discount, coupon_weights)

    for i, r in enumerate(rows):
        coupon_s  = coupon_shares.get(i, Decimal("0.00"))
        taxable   = (r["gross"] - r["item_disc"] - coupon_s).quantize(MONEY_ROUND)
        gst_amt   = (taxable * Decimal(str(r["gst_rate"])) / Decimal("100")).quantize(MONEY_ROUND)
        cgst_amt  = (gst_amt / Decimal("2")).quantize(MONEY_ROUND)
        sgst_amt  = gst_amt - cgst_amt   # exact paisa
        row_payable = (taxable + gst_amt).quantize(MONEY_ROUND)

        r.update({
            "coupon_share":  coupon_s,
            "taxable":       taxable,
            "gst_amt":       gst_amt,
            "cgst_amt":      cgst_amt,
            "sgst_amt":      sgst_amt,
            "row_payable":   row_payable,
        })

    # ── other_charges share ∝ row_payable ────────────────────────────────────
    rp_weights = {i: rows[i]["row_payable"] for i in range(len(rows))}
    other_shares   = _split_proportionally(other_charges, rp_weights)
    roundoff_shares = _split_proportionally(round_off,    rp_weights)

    for i, r in enumerate(rows):
        r["other_share"]    = other_shares.get(i, Decimal("0.00"))
        r["roundoff_share"] = roundoff_shares.get(i, Decimal("0.00"))
        r["final_row_amount"] = (
            r["row_payable"] + r["other_share"] + r["roundoff_share"]
        ).quantize(MONEY_ROUND)

    # ── reconcile to net_payable ──────────────────────────────────────────────
    total_final = sum(r["final_row_amount"] for r in rows)
    diff = net_payable - total_final
    if diff != Decimal("0.00") and rows:
        # Assign difference to largest row
        largest_idx = max(range(len(rows)), key=lambda i: rows[i]["final_row_amount"])
        rows[largest_idx]["final_row_amount"] = (
            rows[largest_idx]["final_row_amount"] + diff
        ).quantize(MONEY_ROUND)

    return rows


# ─────────────────────────────────────────────────────────────────────────────

def calculate_receipt_split(
    matched_items: List[Dict[str, Any]],
    extra_items: List[Dict[str, Any]],
    tax: Decimal,
    discount: Decimal,
    other_charges: Decimal,
    total: Decimal,
    shopper_user_id: int,
    all_room_member_ids: List[int],
    member_name_map: Dict[int, str],
    tax_split_mode: str = "proportional",  # kept for backward compat, not used
    # rich fields for per-item calc
    coupon_discount: Decimal = Decimal("0.00"),
    round_off: Decimal = Decimal("0.00"),
) -> Dict[str, Any]:
    """
    Compile member subtotals, distribute taxes/discounts/charges per-item,
    and calculate debts owed to the shopper.
    sum(member shares) == receipt total EXACTLY.
    """
    # Build flat list of receipt rows with user assignments
    # Each row: {name, quantity, unit_price, line_total, item_discount, gst_rate,
    #            assignments: [{user_id, quantity, amount}]}
    all_rows: List[Dict[str, Any]] = []
    for m in matched_items:
        all_rows.append({**m.get("_orig", m), **m, "assignments": m.get("assignments", [])})
    for e in extra_items:
        all_rows.append({**e.get("_orig", e), **e, "assignments": e.get("assignments", [])})

    # ── per-item allocation ────────────────────────────────────────────────────
    allocated = allocate_per_item(all_rows, coupon_discount, other_charges, round_off, total)

    # ── distribute final_row_amount across assigned users ────────────────────
    member_item_rows: Dict[int, List[Dict]] = defaultdict(list)
    member_subtotals: Dict[int, Decimal]    = defaultdict(lambda: Decimal("0.00"))
    member_discount:  Dict[int, Decimal]    = defaultdict(lambda: Decimal("0.00"))
    member_gst:       Dict[int, Decimal]    = defaultdict(lambda: Decimal("0.00"))
    member_cgst:      Dict[int, Decimal]    = defaultdict(lambda: Decimal("0.00"))
    member_sgst:      Dict[int, Decimal]    = defaultdict(lambda: Decimal("0.00"))
    member_other:     Dict[int, Decimal]    = defaultdict(lambda: Decimal("0.00"))
    member_roundoff:  Dict[int, Decimal]    = defaultdict(lambda: Decimal("0.00"))
    member_total:     Dict[int, Decimal]    = defaultdict(lambda: Decimal("0.00"))

    for i, row_alloc in enumerate(allocated):
        src_row = all_rows[i]
        assignments = src_row.get("assignments", [])
        final_amt   = row_alloc["final_row_amount"]

        if not assignments:
            # Assign to shopper
            assignments = [{
                "user_id": shopper_user_id,
                "quantity": src_row.get("quantity", Decimal("1")),
                "amount": final_amt,
            }]

        # Split final_row_amount equally across assigned users
        uids = [a["user_id"] for a in assignments]
        n    = len(uids)
        user_shares = _split_equally(final_amt, uids)

        # Proportionally split discount/gst/other/roundoff across same users
        user_disc_shares    = _split_equally(row_alloc["item_disc"] + row_alloc["coupon_share"], uids)
        user_gst_shares     = _split_equally(row_alloc["gst_amt"],       uids)
        user_cgst_shares    = _split_equally(row_alloc["cgst_amt"],      uids)
        user_sgst_shares    = _split_equally(row_alloc["sgst_amt"],      uids)
        user_other_shares   = _split_equally(row_alloc["other_share"],   uids)
        user_ro_shares      = _split_equally(row_alloc["roundoff_share"], uids)

        for a in assignments:
            uid = a["user_id"]
            share = user_shares.get(uid, Decimal("0.00"))
            member_item_rows[uid].append({
                "name":          row_alloc["name"],
                "quantity":      a.get("quantity", Decimal("1")),
                "gross":         row_alloc["gross"],
                "item_disc":     row_alloc["item_disc"],
                "coupon_share":  row_alloc["coupon_share"],
                "taxable":       row_alloc["taxable"],
                "gst_rate":      row_alloc["gst_rate"],
                "gst_amt":       row_alloc["gst_amt"],
                "cgst_amt":      row_alloc["cgst_amt"],
                "sgst_amt":      row_alloc["sgst_amt"],
                "row_payable":   row_alloc["row_payable"],
                "other_share":   row_alloc["other_share"],
                "roundoff_share":row_alloc["roundoff_share"],
                "final_amount":  share,
                "is_extra":      src_row.get("is_extra", False),
            })
            member_subtotals[uid] += row_alloc["gross"]
            member_discount[uid]  += user_disc_shares.get(uid, Decimal("0.00"))
            member_gst[uid]       += user_gst_shares.get(uid, Decimal("0.00"))
            member_cgst[uid]      += user_cgst_shares.get(uid, Decimal("0.00"))
            member_sgst[uid]      += user_sgst_shares.get(uid, Decimal("0.00"))
            member_other[uid]     += user_other_shares.get(uid, Decimal("0.00"))
            member_roundoff[uid]  += user_ro_shares.get(uid, Decimal("0.00"))
            member_total[uid]     += share

    # Ensure shopper present
    if shopper_user_id not in member_total:
        member_total[shopper_user_id] = Decimal("0.00")

    # ── exact reconciliation ──────────────────────────────────────────────────
    total_reconciled = sum(member_total.values())
    diff = total - total_reconciled
    if diff != Decimal("0.00") and member_total:
        largest_uid = max(member_total, key=lambda k: member_total[k])
        member_total[largest_uid] = (member_total[largest_uid] + diff).quantize(MONEY_ROUND)

    # ── build summaries ────────────────────────────────────────────────────────
    member_summaries = []
    for uid in sorted(member_total.keys()):
        net_share    = member_total[uid]
        is_shopper   = (uid == shopper_user_id)
        owed         = Decimal("0.00") if is_shopper else net_share

        member_summaries.append({
            "user_id":        uid,
            "display_name":   member_name_map.get(uid, f"User {uid}"),
            "is_shopper":     is_shopper,
            "items_count":    len(member_item_rows[uid]),
            "items":          member_item_rows[uid],
            "subtotal":       member_subtotals[uid],
            "discount_share": member_discount[uid],
            "tax_share":      member_gst[uid],
            "cgst_share":     member_cgst[uid],
            "sgst_share":     member_sgst[uid],
            "other_share":    member_other[uid],
            "roundoff_share": member_roundoff[uid],
            "net_total_share": net_share,
            "owed_to_shopper": owed,
        })

    debts = [
        {"payer_user_id": m["user_id"], "payee_user_id": shopper_user_id, "amount": m["owed_to_shopper"]}
        for m in member_summaries
        if not m["is_shopper"] and m["owed_to_shopper"] > Decimal("0.00")
    ]

    return {
        "member_summaries":  member_summaries,
        "debts":             debts,
        "allocated_rows":    allocated,
        "receipt_total":     total,
        "reconciled_sum":    sum(m["net_total_share"] for m in member_summaries),
    }
